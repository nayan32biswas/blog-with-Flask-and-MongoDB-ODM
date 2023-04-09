from typing import Any, Dict

from flask import Response, json
from werkzeug.exceptions import HTTPException


def custom_response(res: Dict[Any, Any], status: int = 200) -> Response:
    return Response(
        mimetype="application/json", response=json.dumps(res), status=status
    )


def http_exception(detail: str, status: int = 400) -> HTTPException:
    return HTTPException(response=custom_response({"detail": detail}, status=status))
