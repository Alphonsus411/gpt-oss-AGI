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


def main(args):
    planner = Planner()  # Punto de integración para metas y modo

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

    tokenizer = get_tokenizer()
    tokens = tokenizer.encode(args.prompt)
    for token, logprob in generator.generate(tokens, stop_tokens=[tokenizer.eot_token], temperature=args.temperature, max_tokens=args.limit, return_logprobs=True):
        tokens.append(token)
        decoded_token = tokenizer.decode([token])
        print(
            f"Generated token: {repr(decoded_token)}, logprob: {logprob}"
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
