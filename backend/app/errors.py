"""Standardized error responses adhering to Section 5.2 and Appendix B."""
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from fastapi.responses import JSONResponse


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_response(self) -> JSONResponse:
        content = {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }
        return JSONResponse(
            status_code=self.status_code,
            content=content,
            headers=self.headers,
        )


def validation_error(message: str, fields: Optional[List[str]] = None) -> AppException:
    return AppException(
        status_code=400,
        code="VALIDATION_ERROR",
        message=message,
        details={"fields": fields or []},
    )
