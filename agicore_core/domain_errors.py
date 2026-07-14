"""Errores de dominio para rutas Responses y gobierno Qualia."""

from __future__ import annotations


class DomainError(RuntimeError):
    """Base para errores controlados sin exponer datos sensibles."""

    code = "domain_error"
    safe_message = "Error controlado del dominio."
    status_code = 400

    def __init__(self, message: str | None = None, *, detail: str | None = None) -> None:
        super().__init__(message or self.safe_message)
        self.detail = detail


class HarmonyParseError(DomainError):
    """Fallo controlado al parsear o renderizar mensajes Harmony."""

    code = "harmony_parse_error"
    safe_message = "No se pudo procesar la conversación Harmony de forma segura."
    status_code = 400


class ToolCallValidationError(DomainError):
    """Fallo controlado al validar una llamada de herramienta."""

    code = "tool_call_validation_error"
    safe_message = "La llamada de herramienta no supera la validación de seguridad."
    status_code = 400


class QualiaPolicyError(DomainError):
    """Fallo crítico o vinculante en una política Qualia."""

    code = "qualia_policy_error"
    safe_message = "La política Qualia no pudo aplicarse de forma segura."
    status_code = 500


class UnsafeOutputBlocked(DomainError):
    """Salida bloqueada por seguridad antes de exponer contenido no redactado."""

    code = "unsafe_output_blocked"
    safe_message = "La salida fue bloqueada por las políticas de seguridad."
    status_code = 400
