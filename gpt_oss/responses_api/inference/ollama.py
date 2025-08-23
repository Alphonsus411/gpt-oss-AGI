"""
NOTA: esta es una implementación improvisada que usa Ollama para la inferencia. Se utiliza
principalmente para pruebas y desarrollo. No aprovecha ningún almacenamiento en caché de
prompts ni otras optimizaciones y, por lo tanto, puede ser lenta entre turnos.
"""

import json
import os
import threading
import time
from typing import Callable, Optional
import requests
from urllib.parse import urlparse

from openai_harmony import load_harmony_encoding, HarmonyEncodingName

EOS_TOKEN = 200002  # emitido en un tiempo de espera forzado
# Valor centinela devuelto cuando no hay un token real disponible. El servidor
# debe ignorar este token y seguir consultando hasta que se genere un token
# válido o EOS.
PAD_TOKEN = 0

# Parámetros ajustables
POLL_INTERVAL_S = 0.01           # 10ms entre comprobaciones del búfer
CALL_MAX_WAIT_S = 0.250          # tiempo máximo de bloqueo en una sola llamada de inferencia
NO_TOKEN_TIMEOUT_S = 15.0        # tiempo de inactividad total antes de emitir EOS
FIRST_BYTE_TIMEOUT_S = 30.0      # tiempo de espera para el primer token antes de EOS
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
    """Gestiona el estado de streaming para una única instancia de modelo Ollama."""

    def __init__(self, model_name: str, endpoint_url: Optional[str] = None):
        self.encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        self.model_name = model_name
        url = endpoint_url or os.environ.get("OLLAMA_ENDPOINT", DEFAULT_ENDPOINT_URL)
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Ollama endpoint must use HTTP or HTTPS, got: {url}"
            )
        self.endpoint_url = url

        # Estado por instancia
        self._token_buffer: list[int] = []
        self._buffer_lock = threading.Lock()
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_done = threading.Event()
        self._stream_error: Optional[Exception] = None
        self._last_progress_ts: float = 0.0
        self._previous_request_tokens: list[int] = []

    # ------------------------------------------------------------------
    # Funciones internas
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
            last_len = 0  # número de tokens ya emitidos

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
    # API pública
    def infer_next_token(
        self, tokens: list[int], temperature: float = 0.0, new_request: bool = False
    ) -> int:
        """Inferir el siguiente token usando el backend de Ollama."""

        if new_request:
            self._reset_stream_state()
            self._stream_thread = self._start_stream(token_ids=tokens, temperature=temperature)
            # Esperar el primer byte dentro de FIRST_BYTE_TIMEOUT_S (sin emitir EOS antes de tiempo)
            start = _now()
            while _now() - start < FIRST_BYTE_TIMEOUT_S:
                with self._buffer_lock:
                    if self._token_buffer:
                        tok = self._token_buffer.pop(0)
                        self._touch_progress()
                        return tok
                if self._stream_error is not None:
                    raise RuntimeError(f"Ollama stream error: {self._stream_error!r}")
                # Si Ollama termina al instante sin salida, continuar el bucle hasta que expire el tiempo
                time.sleep(POLL_INTERVAL_S)
            # Tiempo de espera estricto del primer byte -> emitir EOS para que el servidor pueda detener la solicitud
            return EOS_TOKEN

        if self._stream_error is not None:
            raise RuntimeError(f"Ollama stream error: {self._stream_error!r}")

        # Ruta normal: esperar hasta CALL_MAX_WAIT_S a que llegue un token
        wait_start = _now()
        while _now() - wait_start < CALL_MAX_WAIT_S:
            with self._buffer_lock:
                if self._token_buffer:
                    tok = self._token_buffer.pop(0)
                    self._touch_progress()
                    return tok
            # Aún no hay token; si hemos estado inactivos demasiado tiempo, finalizar con EOS
            if _now() - self._last_progress_ts > NO_TOKEN_TIMEOUT_S:
                return EOS_TOKEN
            time.sleep(POLL_INTERVAL_S)

        # Aún no hay token en esta fracción de llamada. NO enviar EOS a menos que se haya agotado el tiempo.
        if _now() - self._last_progress_ts > NO_TOKEN_TIMEOUT_S:
            return EOS_TOKEN

        # Indicar al llamador que nos invoque de nuevo; bloquear lo mínimo devolviendo *nada nuevo*.
        # Debemos devolver un entero; lo más seguro es esperar un poco más por un token.
        # Si aún no hay, seguir devolviendo solo tras breves esperas. Evitar EOS aquí.
        # Una espera corta más para reducir el bucle caliente:
        time.sleep(POLL_INTERVAL_S)
        with self._buffer_lock:
            if self._token_buffer:
                tok = self._token_buffer.pop(0)
                self._touch_progress()
                return tok

        # Como último recurso para esta fracción de llamada, devolver EOS solo en un verdadero tiempo de inactividad.
        if _now() - self._last_progress_ts > NO_TOKEN_TIMEOUT_S:
            return EOS_TOKEN

        # Si llegamos aquí, aún no hemos obtenido un token; pedir al llamador que vuelva a invocar pronto.
        # Indicamos "aún no hay token" devolviendo PAD_TOKEN; se espera que el servidor descarte
        # este valor y continúe consultando hasta que se produzca un token real o EOS.
        return PAD_TOKEN


def setup_model(checkpoint: str, endpoint_url: Optional[str] = None) -> Callable[[list[int], float, bool], int]:
    """Crear un modelo de streaming invocable para el checkpoint dado."""
    streamer = OllamaStreamer(checkpoint, endpoint_url=endpoint_url)
    return streamer.infer_next_token
