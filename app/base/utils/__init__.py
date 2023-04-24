from datetime import date, datetime
from typing import Any, Optional, no_type_check

from flask import request
from pydantic import BaseModel, ValidationError
from pydantic.utils import deep_update
from werkzeug.exceptions import HTTPException

from app.base.utils.response import custom_response, http_exception


def calculate_offset(page: int, limit: int) -> int:
    return (page - 1) * limit


def get_offset(page: int, limit: int) -> int:
    if not 1 <= limit <= 100:
        raise ValueError("Invalid pagination limit")
    return calculate_offset(page, limit)


@no_type_check
def update_partially(target, source: BaseModel, exclude: Optional[Any] = None):
    cls = target.__class__
    update_data = source.dict(exclude_unset=True, exclude=exclude)
    dict_data = target.dict(exclude=cls.get_relational_field_info().keys())
    target = cls(**deep_update(dict_data, update_data))
    return target


def date_to_datetime(val: date) -> datetime:
    return datetime(val.year, val.month, val.day)


@no_type_check
def parse_json(Schema):
    try:
        return Schema(**request.get_json())
    except ValidationError as ex:
        raise HTTPException(
            response=custom_response({"detail": ex.errors()}, status=422)
        )
    except Exception:
        raise HTTPException(
            response=custom_response({"detail": "Unhandled parsing error."}, status=500)
        )
