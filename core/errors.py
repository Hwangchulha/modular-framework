
class FrameworkError(Exception):
    code = "ERR_INTERNAL"
    def __init__(self, message: str, *, code: str | None = None, details=None):
        super().__init__(message)
        self.code = code or self.code
        self.details = details

class UnsupportedMode(FrameworkError):
    code = "ERR_UNSUPPORTED_MODE"

class AuthzDenied(FrameworkError):
    code = "ERR_FORBIDDEN"

class ManifestError(FrameworkError):
    code = "ERR_MANIFEST"

class SchemaValidationError(FrameworkError):
    code = "ERR_SCHEMA"

class ModuleExecutionError(FrameworkError):
    code = "ERR_MODULE"
