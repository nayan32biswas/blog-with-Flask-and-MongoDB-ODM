from fastapi import Request
from fastapi.responses import JSONResponse

from app.base.exceptions import CustomException, UnicornException


async def unicorn_exception_handler(
    request: Request, exc: UnicornException
) -> JSONResponse:
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name} did something. There goes a rainbow..."},
    )


async def handle_custom_exception(
    request: Request, exc: CustomException
) -> JSONResponse:
    error_obj = {
        "code": exc.code,
        "detail": exc.detail,
    }
    if exc.field:
        error_obj["field"] = exc.field
    return JSONResponse(status_code=exc.status_code, content={"errors": [error_obj]})
