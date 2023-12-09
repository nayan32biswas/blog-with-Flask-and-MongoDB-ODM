import logging
from typing import Any

from app.base.utils.response import ExType, http_exception

logger = logging.getLogger(__name__)


def catch_exceptions_middleware(e: Any) -> Any:
    logger.critical(f"""Unhandled Error:{e}""")
    return http_exception(
        status=500,
        code=ExType.INTERNAL_SERVER_ERROR,
        detail="Internal server error. Try later.",
    )
