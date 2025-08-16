"""
NOTE: this is a stiched together implementation that uses Ollama for inference. It's primarily used
for testing and development. It does not leverage any prompt caching or other optimizations and
can therefore be slow between turns.
"""

import json
import os
import threading
import time
from typing import Callable, Optional
import requests

from openai_harmony import load_harmony_encoding, HarmonyEncodingName

EOS_TOKEN = 200002  # emitted on hard timeout
# Sentinel value returned when no real token is available. The server must
# ignore this token and continue polling until a valid token or EOS is
# produced.
PAD_TOKEN = 0

# Tunables
POLL_INTERVAL_S = 0.01           # 10ms between buffer checks
CALL_MAX_WAIT_S = 0.250          # max time to block inside a single infer call
NO_TOKEN_TIMEOUT_S = 15.0        # overall inactivity timeout before emitting EOS
FIRST_BYTE_TIMEOUT_S = 30.0      # time to wait for first token before EOS
DEFAULT_ENDPOINT_URL = "http://localhost:11434/api/generate"


def _now() -> float:
    return time.monotonic()


def lcp(cache: list[int], inp: list[int]) -> list[int]:
    i = 0
    max_len = min(len(cache), len(inp))
    while i < max_len and cache[i] == inp[i]:
        i += 1
    return cache[:i]


class OllamaStreamer:
    """Handle streaming state for a single Ollama model instance."""

    def __init__(self, model_name: str, endpoint_url: Optional[str] = None):
        self.encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        self.model_name = model_name
        self.endpoint_url = endpoint_url or os.environ.get("OLLAMA_ENDPOINT", DEFAULT_ENDPOINT_URL)

        # Per-instance state
        self._token_buffer: list[int] = []
        self._buffer_lock = threading.Lock()
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_done = threading.Event()
        self._stream_error: Optional[Exception] = None
        self._last_progress_ts: float = 0.0
        self._previous_request_tokens: list[int] = []

    # ------------------------------------------------------------------
    # Internal helpers
    def _touch_progress(self) -> None:
        self._last_progress_ts = _now()

    def _reset_stream_state(self) -> None:
        with self._buffer_lock:
            self._token_buffer = []
        self._stream_done.clear()
        self._stream_thread = None
        self._stream_error = None
        self._touch_progress()

    def _start_stream(self, token_ids: list[int], temperature: float):
        prompt_text = self.encoding.decode(token_ids)

        def run():
            nonlocal prompt_text, temperature

            accum_text = ""
            last_len = 0  # number of tokens already emitted

            try:
                url = self.endpoint_url
                context = None
                if len(self._previous_request_tokens) > 0:
                    context = self._previous_request_tokens

                payload = {
                    "model": self.model_name,
                    "prompt": prompt_text,
                    "stream": True,
                    "context": context,
                    "options": {"temperature": temperature},
                }

                with requests.post(url, json=payload, stream=True, timeout=60) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        obj = json.loads(line)

                        if isinstance(obj.get("response"), str):
                            accum_text += obj["response"]
                            toks = self.encoding.encode(accum_text, allowed_special="all")
                            if len(toks) > last_len:
                                new_toks = toks[last_len:]
                                with self._buffer_lock:
                                    self._token_buffer.extend(new_toks)
                                last_len = len(toks)
                                self._touch_progress()

                        if obj.get("done", False):
                            with self._buffer_lock:
                                self._token_buffer.append(EOS_TOKEN)
                            last_len = len(toks)
                            self._touch_progress()
                            context = obj.get("context")
                            if context and len(context) > 0:
                                with self._buffer_lock:
                                    self._previous_request_tokens = context
                            break

                self._stream_done.set()

            except Exception as e:
                self._stream_error = e
                self._stream_done.set()

        t = threading.Thread(target=run, name="ollama-stream", daemon=True)
        t.start()
        return t

    # ------------------------------------------------------------------
    # Public API
    def infer_next_token(
        self, tokens: list[int], temperature: float = 0.0, new_request: bool = False
    ) -> int:
        """Infer the next token using the Ollama backend."""

        if new_request:
            self._reset_stream_state()
            self._stream_thread = self._start_stream(token_ids=tokens, temperature=temperature)
            # Wait for first byte within FIRST_BYTE_TIMEOUT_S (without emitting EOS early)
            start = _now()
            while _now() - start < FIRST_BYTE_TIMEOUT_S:
                with self._buffer_lock:
                    if self._token_buffer:
                        tok = self._token_buffer.pop(0)
                        self._touch_progress()
                        return tok
                if self._stream_error is not None:
                    raise RuntimeError(f"Ollama stream error: {self._stream_error!r}")
                # If Ollama finished instantly with no output, continue loop until timeout
                time.sleep(POLL_INTERVAL_S)
            # Hard first-byte timeout -> emit EOS so the server can stop this request
            return EOS_TOKEN

        if self._stream_error is not None:
            raise RuntimeError(f"Ollama stream error: {self._stream_error!r}")

        # Normal path: wait up to CALL_MAX_WAIT_S for a token to arrive
        wait_start = _now()
        while _now() - wait_start < CALL_MAX_WAIT_S:
            with self._buffer_lock:
                if self._token_buffer:
                    tok = self._token_buffer.pop(0)
                    self._touch_progress()
                    return tok
            # No token yet; if we've been idle too long overall, end with EOS
            if _now() - self._last_progress_ts > NO_TOKEN_TIMEOUT_S:
                return EOS_TOKEN
            time.sleep(POLL_INTERVAL_S)

        # Still no token in this call slice. Do NOT send EOS unless we've timed out.
        if _now() - self._last_progress_ts > NO_TOKEN_TIMEOUT_S:
            return EOS_TOKEN

        # Tell caller to call us again; block minimally by returning *nothing new*.
        # We must return an int; safest is to wait a tiny bit longer for a token.
        # If still none, keep returning only after short waits. Avoid EOS here.
        # One more short wait to reduce hot-looping:
        time.sleep(POLL_INTERVAL_S)
        with self._buffer_lock:
            if self._token_buffer:
                tok = self._token_buffer.pop(0)
                self._touch_progress()
                return tok

        # As a last resort for this call slice, return EOS only on true inactivity timeout.
        if _now() - self._last_progress_ts > NO_TOKEN_TIMEOUT_S:
            return EOS_TOKEN

        # If we reach here, we still haven't got a token—ask the caller to call again soon.
        # We signal "no token yet" by returning PAD_TOKEN; the server is expected to drop
        # this value and continue polling until a real token or EOS is produced.
        return PAD_TOKEN


def setup_model(checkpoint: str, endpoint_url: Optional[str] = None) -> Callable[[list[int], float, bool], int]:
    """Create a streaming model callable for the given checkpoint."""
    streamer = OllamaStreamer(checkpoint, endpoint_url=endpoint_url)
    return streamer.infer_next_token
