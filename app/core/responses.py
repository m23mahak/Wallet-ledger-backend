"""Consistent JSON response shapes."""
from fastapi.responses import JSONResponse


def error_response(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"success": False, "error": error})
