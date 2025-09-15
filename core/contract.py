
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

Mode = Literal["SINGLE", "BULK"]

class Options(BaseModel):
    continue_on_error: Optional[bool] = None
    parallelism: Optional[int] = None
    transactional: Optional[bool] = None
    dry_run: Optional[bool] = None
    auto_fanout: Optional[bool] = None

class InEnvelope(BaseModel):
    action: str
    mode: Mode = "SINGLE"
    input: Optional[Dict[str, Any]] = None
    inputs: Optional[List[Dict[str, Any]]] = None
    options: Optional[Options] = None
    request_id: Optional[str] = None

class ErrorObj(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ResultItem(BaseModel):
    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorObj] = None
    index: Optional[int] = None
    id: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

class OutEnvelope(BaseModel):
    ok: bool
    mode: Mode
    data: Optional[Dict[str, Any]] = None
    results: Optional[List[ResultItem]] = None
    error: Optional[ErrorObj] = None
    metrics: Optional[Dict[str, Any]] = None
    partial_ok: Optional[bool] = None

class Context(BaseModel):
    request_id: Optional[str] = None
    vars: Dict[str, Any] = Field(default_factory=dict)
    secrets: Dict[str, str] = Field(default_factory=dict)
    scopes: List[str] = Field(default_factory=list)
