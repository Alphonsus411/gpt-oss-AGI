"""
NOTA: esta no es la forma más eficiente de usar transformers. Es una implementación sencilla que infiere
un token a la vez para imitar el comportamiento de la implementación de Triton.
"""

import os
from typing import Callable, List

# Importaciones de Transformers
from transformers import AutoModelForCausalLM, PreTrainedModel
import torch


DEFAULT_TEMPERATURE = 0.0
TP = os.environ.get("TP", 2)

def load_model(checkpoint: str):
    """
    Sirve el modelo directamente con la API Auto.
    """

    model = AutoModelForCausalLM.from_pretrained(
        checkpoint,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    return model


def get_infer_next_token(model: PreTrainedModel):
    """
    Devuelve una función invocable con la misma forma que la implementación original de Triton:
      infer_next_token(tokens: List[int], temperature: float, new_request: bool) -> int

    Detalle de implementación:
      - Realizamos una generación de un solo token usando ``model.generate``.
      - ``generate`` maneja el muestreo (``temperature=0`` => codicioso, de lo contrario, muestreo).
    """

    def infer_next_token(
        tokens: List[int],
        temperature: float = DEFAULT_TEMPERATURE,
        new_request: bool = False, # se mantiene para compatibilidad de la interfaz; aquí no se usa
    ) -> int:
        tokens = torch.tensor([tokens], dtype=torch.int64, device=model.device)
        output = model.generate(tokens, max_new_tokens=1, do_sample=temperature != 0, temperature=temperature)
        return output[0, -1].tolist()

    return infer_next_token


def setup_model(checkpoint: str) -> Callable[[List[int], float, bool], int]:
    model = load_model(checkpoint)
    infer_next_token = get_infer_next_token(model)
    return infer_next_token
