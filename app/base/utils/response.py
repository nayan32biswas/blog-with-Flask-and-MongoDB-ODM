from typing import Any, Dict
from flask import json, Response

from werkzeug.exceptions import HTTPException


def custom_response(res: Dict[Any, Any], status: int = 200) -> Response:
    return Response(
        mimetype="application/json", response=json.dumps(res), status=status
    )


def http_exception(detail: str, status: int = 400):
    return HTTPException(response=custom_response({"detail": detail}, status=status))
