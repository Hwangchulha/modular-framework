from typing import Any, Optional, Dict

class FrameworkError(Exception):
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.http_status = http_status

def err_schema(msg: str, details: Optional[Dict[str, Any]] = None) -> FrameworkError:
    return FrameworkError("ERR_SCHEMA", msg, details, 400)

def err_forbidden(msg: str, details: Optional[Dict[str, Any]] = None) -> FrameworkError:
    return FrameworkError("ERR_FORBIDDEN", msg, details, 403)

def err_secret(msg: str, details: Optional[Dict[str, Any]] = None) -> FrameworkError:
    return FrameworkError("ERR_SECRET", msg, details, 500)

def err_unsupported_mode(msg: str, details: Optional[Dict[str, Any]] = None) -> FrameworkError:
    return FrameworkError("ERR_UNSUPPORTED_MODE", msg, details, 400)

def err_internal(msg: str, details: Optional[Dict[str, Any]] = None) -> FrameworkError:
    return FrameworkError("ERR_INTERNAL", msg, details, 500)

def err_rate_limit(msg: str, details: Optional[Dict[str, Any]] = None) -> FrameworkError:
    return FrameworkError("ERR_RATE_LIMIT", msg, details, 429)

def err_timeout(msg: str, details: Optional[Dict[str, Any]] = None) -> FrameworkError:
    return FrameworkError("ERR_TIMEOUT", msg, details, 504)

def err_circuit_open(msg: str, details: Optional[Dict[str, Any]] = None) -> FrameworkError:
    return FrameworkError("ERR_CIRCUIT_OPEN", msg, details, 503)
