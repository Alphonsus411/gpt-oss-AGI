from __future__ import annotations

import math
from typing import Any, Literal, Optional, Union

from openai_harmony import ReasoningEffort
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StrictBool, StrictInt, StrictStr, field_validator, model_validator

MODEL_IDENTIFIER = "gpt-oss-120b"
DEFAULT_TEMPERATURE = 0.0
REASONING_EFFORT = ReasoningEffort.LOW
DEFAULT_MAX_OUTPUT_TOKENS = 10_000

RESERVED_INTERNAL_FIELDS = frozenset(
    {
        "pro_vida",
        "no_dano",
        "respeto",
        "qualia",
        "qualia_policies",
        "ethical_score",
        "violated_constraints",
        "governance_score",
        "governance_scores",
        "internal_governance_score",
        "internal_governance_scores",
        "government_score",
        "government_scores",
        "policy_score",
        "policy_scores",
        "safety_score",
        "safety_scores",
        "risk_score",
        "risk_scores",
    }
)

JsonScalar = Union[StrictStr, StrictInt, FiniteFloat, StrictBool, None]
JsonValue = Any


def _validate_json_value(value: Any, *, location: str) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{location} no acepta NaN ni Infinity")
    elif isinstance(value, (str, int, bool)) or value is None:
        return value
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_json_value(child, location=f"{location}[{index}]")
    elif isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{location} solo acepta claves string")
            _validate_json_value(child, location=f"{location}.{key}")
    else:
        raise ValueError(f"{location} contiene un valor JSON inválido")
    return value


def _contains_reserved_internal_name(name: str) -> bool:
    normalized = name.strip().lower()
    return normalized in RESERVED_INTERNAL_FIELDS or (
        normalized.endswith("_score")
        and any(marker in normalized for marker in ("govern", "policy", "safety", "risk", "ethical"))
    )


def _validate_no_reserved_internal_fields(value: Any, *, location: str) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{location} solo acepta claves string")
            if _contains_reserved_internal_name(key):
                raise ValueError(
                    f"{location} no puede contener el campo interno reservado '{key}'"
                )
            _validate_no_reserved_internal_fields(child, location=f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_no_reserved_internal_fields(child, location=f"{location}[{index}]")
    return value


class StrictApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StrictMetadata(StrictApiModel):
    """Client metadata: JSON-only values and no Qualia/governance internals."""

    model_config = ConfigDict(extra="allow", strict=True)

    @model_validator(mode="before")
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("metadata debe ser un objeto JSON")
        _validate_json_value(value, location="metadata")
        return _validate_no_reserved_internal_fields(value, location="metadata")


class InternalQualiaFields(StrictApiModel):
    """Server-only Qualia fields. Never accept this model from client input."""

    pro_vida: Optional[FiniteFloat] = None
    no_dano: Optional[FiniteFloat] = None
    respeto: Optional[FiniteFloat] = None
    qualia: Optional[dict[str, JsonValue]] = None
    qualia_policies: Optional[list[StrictStr]] = None
    ethical_score: Optional[FiniteFloat] = None
    violated_constraints: Optional[list[StrictStr]] = None
    governance_scores: Optional[dict[str, FiniteFloat]] = None


class NumericSignal(StrictApiModel):
    name: StrictStr
    value: FiniteFloat


class UrlCitation(StrictApiModel):
    type: Literal["url_citation"]
    end_index: StrictInt
    start_index: StrictInt
    url: StrictStr
    title: StrictStr


class TextContentItem(StrictApiModel):
    type: Union[Literal["text"], Literal["input_text"], Literal["output_text"]]
    text: StrictStr
    status: Optional[StrictStr] = "completed"
    annotations: Optional[list[UrlCitation]] = None


class SummaryTextContentItem(StrictApiModel):
    type: Literal["summary_text"]
    text: StrictStr


class ReasoningTextContentItem(StrictApiModel):
    type: Literal["reasoning_text"]
    text: StrictStr


class ReasoningItem(StrictApiModel):
    id: StrictStr = "rs_1234"
    type: Literal["reasoning"]
    summary: list[SummaryTextContentItem]
    content: Optional[list[ReasoningTextContentItem]] = Field(default_factory=list)


class Item(StrictApiModel):
    type: Optional[Literal["message"]] = "message"
    role: Literal["user", "assistant", "system"]
    content: Union[list[TextContentItem], StrictStr]
    status: Union[Literal["in_progress", "completed", "incomplete"], None] = None


class FunctionCallItem(StrictApiModel):
    type: Literal["function_call"]
    name: StrictStr = Field(min_length=1)
    arguments: StrictStr
    status: Literal["in_progress", "completed", "incomplete"] = "completed"
    id: StrictStr = "fc_1234"
    call_id: StrictStr = "call_1234"


class FunctionCallOutputItem(StrictApiModel):
    type: Literal["function_call_output"]
    call_id: StrictStr = "call_1234"
    output: StrictStr


class WebSearchActionSearch(StrictApiModel):
    type: Literal["search"]
    query: Optional[StrictStr] = None


class WebSearchActionOpenPage(StrictApiModel):
    type: Literal["open_page"]
    url: Optional[StrictStr] = None


class WebSearchActionFind(StrictApiModel):
    type: Literal["find"]
    pattern: Optional[StrictStr] = None
    url: Optional[StrictStr] = None


class WebSearchCallItem(StrictApiModel):
    type: Literal["web_search_call"]
    id: StrictStr = "ws_1234"
    status: Literal["in_progress", "completed", "incomplete"] = "completed"
    action: Union[WebSearchActionSearch, WebSearchActionOpenPage, WebSearchActionFind]


class Error(StrictApiModel):
    code: StrictStr
    message: StrictStr


class IncompleteDetails(StrictApiModel):
    reason: StrictStr


class Usage(StrictApiModel):
    input_tokens: StrictInt
    output_tokens: StrictInt
    total_tokens: StrictInt


class FunctionToolDefinition(StrictApiModel):
    type: Literal["function"]
    name: StrictStr = Field(min_length=1)
    parameters: dict[str, JsonValue]
    strict: StrictBool = False
    description: Optional[StrictStr] = ""

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _validate_json_value(value, location="tools.parameters")
        _validate_no_reserved_internal_fields(value, location="tools.parameters")
        return value


class BrowserToolConfig(StrictApiModel):
    type: Literal["browser_search"]


class ReasoningConfig(StrictApiModel):
    effort: Literal["low", "medium", "high"] = "low"


class ResponsesRequest(StrictApiModel):
    instructions: Optional[StrictStr] = None
    max_output_tokens: Optional[StrictInt] = DEFAULT_MAX_OUTPUT_TOKENS
    input: Union[
        StrictStr, list[Union[Item, ReasoningItem, FunctionCallItem, FunctionCallOutputItem, WebSearchCallItem]]
    ]
    model: Optional[StrictStr] = MODEL_IDENTIFIER
    stream: Optional[StrictBool] = False
    tools: Optional[list[Union[FunctionToolDefinition, BrowserToolConfig]]] = Field(default_factory=list)
    reasoning: Optional[ReasoningConfig] = Field(default_factory=ReasoningConfig)
    metadata: Optional[StrictMetadata] = Field(default_factory=StrictMetadata)
    tool_choice: Optional[Literal["auto", "none"]] = "auto"
    parallel_tool_calls: Optional[StrictBool] = False
    store: Optional[StrictBool] = False
    previous_response_id: Optional[StrictStr] = None
    temperature: Optional[FiniteFloat] = DEFAULT_TEMPERATURE
    include: Optional[list[StrictStr]] = None

    @model_validator(mode="before")
    @classmethod
    def reject_client_internal_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            _validate_no_reserved_internal_fields(value, location="request")
        return value

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return value
        if not math.isfinite(value):
            raise ValueError("temperature debe ser un número finito")
        if value < 0 or value > 2:
            raise ValueError("temperature debe estar entre 0 y 2")
        return value


class ResponseObject(StrictApiModel):
    output: list[Union[Item, ReasoningItem, FunctionCallItem, FunctionCallOutputItem, WebSearchCallItem]]
    created_at: StrictInt
    usage: Optional[Usage] = None
    status: Literal["completed", "failed", "incomplete", "in_progress"] = "in_progress"
    background: None = None
    error: Optional[Error] = None
    incomplete_details: Optional[IncompleteDetails] = None
    instructions: Optional[StrictStr] = None
    max_output_tokens: Optional[StrictInt] = None
    max_tool_calls: Optional[StrictInt] = None
    metadata: Optional[dict[str, JsonValue]] = Field(default_factory=dict)
    model: Optional[StrictStr] = MODEL_IDENTIFIER
    parallel_tool_calls: Optional[StrictBool] = False
    previous_response_id: Optional[StrictStr] = None
    id: Optional[StrictStr] = "resp_1234"
    object: Optional[StrictStr] = "response"
    text: Optional[dict[str, JsonValue]] = None
    tool_choice: Optional[StrictStr] = "auto"
    top_p: Optional[StrictInt] = 1
