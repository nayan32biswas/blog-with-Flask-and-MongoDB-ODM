from enum import Enum
from typing import Any, Dict, Optional

from flask import Response, json
from werkzeug.exceptions import HTTPException


class ExType(str, Enum):
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    UNHANDLED_ERROR = "UNHANDLED_ERROR"

    OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    USERNAME_EXISTS = "USERNAME_EXISTS"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"


def custom_response(res: Dict[Any, Any], status: int = 200) -> Response:
    return Response(
        mimetype="application/json", response=json.dumps(res), status=status
    )


def http_exception(
    status: int, code: ExType, detail: str, field: Optional[str] = None
) -> HTTPException:
    return HTTPException(
        response=custom_response(
            {"code": code, "detail": detail, "field": field}, status=status
        )
    )
