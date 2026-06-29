# Inferencia paralela de modelos
# Nota: Este script es solo para fines de demostración. No está diseñado para uso en producción.
#       Consulte gpt_oss.chat para un ejemplo más completo con el parser Harmony.
# Ejemplo de uso:
# torchrun --nproc-per-node=4 -m gpt_oss.generate -p "¿por qué cruzó la carretera la gallina?" model/
#
# Incluye un ``Planner`` que permite consultar metas y modos del agente.

import argparse

from gpt_oss.planner import Planner  # Gestiona metas y modos del agente
from gpt_oss.tokenizer import get_tokenizer
from agicore_core.qualia_engine import CoreQualiaEngine


class QualiaControlledTokenGenerator:
    """Envuelve un generador para que Qualia gobierne cada paso de token."""

    def __init__(self, generator, tokenizer, qualia_engine):
        self.generator = generator
        self.tokenizer = tokenizer
        self.qualia_engine = qualia_engine

    def generate(self, tokens, *, prompt_state, temperature, limit):
        decoded_text = prompt_state.get("prompt", "")
        stream = self.generator.generate(
            tokens,
            stop_tokens=[self.tokenizer.eot_token],
            temperature=temperature,
            max_tokens=limit,
            return_logprobs=True,
        )
        stream = iter(stream)
        while True:
            pre_state, blocked = self.qualia_engine.govern_decision(
                {
                    **prompt_state,
                    "task": "token_generation",
                    "decoded_text": decoded_text,
                    "last_token": tokens[-1] if tokens else None,
                },
                phase="token_generation:pre",
            )
            if blocked is not None:
                self.qualia_engine.after_decision(
                    blocked, pre_state, phase="token_generation:pre"
                )
                yield None, None, blocked
                return

            try:
                token, logprob = next(stream)
            except StopIteration:
                return

            decoded_token = self.tokenizer.decode([token])
            token_state, blocked = self.qualia_engine.govern_decision(
                {
                    **pre_state,
                    "token": decoded_token,
                    "last_token": decoded_token,
                    "decoded_text": decoded_text + decoded_token,
                },
                phase="token_generation:post",
            )
            if blocked is not None:
                self.qualia_engine.after_decision(
                    blocked, token_state, phase="token_generation:post"
                )
                yield None, None, blocked
                return

            decoded_text += decoded_token
            self.qualia_engine.after_decision(
                {"token": decoded_token, "logprob": logprob},
                token_state,
                phase="token_generation",
            )
            yield token, logprob, None


def main(args):
    planner = Planner()  # Punto de integración para metas y modo
    qualia_engine = CoreQualiaEngine()

    match args.backend:
        case "torch":
            from gpt_oss.torch.utils import init_distributed
            from gpt_oss.torch.model import TokenGenerator as TorchGenerator
            device = init_distributed()
            generator = TorchGenerator(args.checkpoint, device=device)
        case "triton":
            from gpt_oss.torch.utils import init_distributed
            from gpt_oss.triton.model import TokenGenerator as TritonGenerator
            device = init_distributed()
            generator = TritonGenerator(args.checkpoint, context=4096, device=device)
        case "vllm":
            from gpt_oss.vllm.token_generator import TokenGenerator as VLLMGenerator
            generator = VLLMGenerator(args.checkpoint, tensor_parallel_size=2)
        case _:
            raise ValueError(f"Invalid backend: {args.backend}")

    prompt_state = {
        "task": "generate",
        "context": "cli",
        "goals": ["safe_generation"],
        "prompt": args.prompt,
    }
    prompt_state, blocked = qualia_engine.govern_decision(prompt_state, phase="generate_prompt")
    if blocked is not None:
        qualia_engine.after_decision(blocked, prompt_state, phase="generate_prompt")
        print(f"Generación bloqueada por Qualia: {blocked}")
        return

    tokenizer = get_tokenizer()
    tokens = tokenizer.encode(args.prompt)
    decoded_text = args.prompt
    controlled_generator = QualiaControlledTokenGenerator(generator, tokenizer, qualia_engine)
    for token, logprob, blocked in controlled_generator.generate(
        tokens,
        prompt_state=prompt_state,
        temperature=args.temperature,
        limit=args.limit,
    ):
        if blocked is not None:
            print(f"Token bloqueado por Qualia: {blocked}")
            break
        tokens.append(token)
        decoded_token = tokenizer.decode([token])
        decoded_text += decoded_token
        print(
            f"Generated token: {repr(decoded_token)}, logprob: {logprob}"
        )
    qualia_engine.after_decision(
        {"tokens": len(tokens), "decoded_text": decoded_text},
        prompt_state,
        phase="generate_response",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejemplo de generación de texto")
    parser.add_argument(
        "checkpoint",
        metavar="ARCHIVO",
        type=str,
        help="Ruta al checkpoint de SafeTensors",
    )
    parser.add_argument(
        "-p",
        "--prompt",
        metavar="PROMPT",
        type=str,
        default="¿Cómo estás?",
        help="Prompt para el LLM",
    )
    parser.add_argument(
        "-t",
        "--temperature",
        metavar="TEMP",
        type=float,
        default=0.0,
        help="Temperatura de muestreo",
    )
    parser.add_argument(
        "-l",
        "--limit",
        metavar="LIMITE",
        type=int,
        default=0,
        help="Límite en el número de tokens (0 para desactivar)",
    )
    parser.add_argument(
        "-b",
        "--backend",
        metavar="BACKEND",
        type=str,
        default="torch",
        choices=["triton", "torch", "vllm"],
        help="Backend de inferencia",
    )
    args = parser.parse_args()

    main(args)
