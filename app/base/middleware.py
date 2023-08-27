import logging
import time
from typing import Any

from fastapi import Request

from app.base.exceptions import CustomException, ExType

from .config import DEBUG

logger = logging.getLogger(__name__)


async def add_process_time_header(request: Request, call_next: Any) -> Any:
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


async def catch_exceptions_middleware(request: Request, call_next: Any) -> Any:
    try:
        return await call_next(request)
    except Exception as e:
        logger.critical(f"""Unhandled Error:{e}""")
        if DEBUG:
            raise e
        else:
            # return Response("Internal server error", status_code=500)
            raise CustomException(
                status_code=500,
                code=ExType.INTERNAL_SERVER_ERROR,
                detail="Internal server error. Try later.",
            )
