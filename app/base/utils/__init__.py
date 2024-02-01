from datetime import date, datetime
from typing import Any, no_type_check

from flask import request
from pydantic import BaseModel, ValidationError
from pydantic.v1.utils import deep_update
from werkzeug.exceptions import HTTPException

from app.base.utils.response import custom_response


@no_type_check
def update_partially(target, source: BaseModel, exclude=None) -> Any:
    cls = target.__class__
    update_data = source.model_dump(exclude_unset=True, exclude=exclude)
    target = cls(
        **deep_update(
            target.model_dump(exclude=cls.get_relational_field_info().keys()),
            update_data,
        )
    )
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
        ) from ex
    except Exception as e:
        raise HTTPException(
            response=custom_response({"detail": "Unhandled parsing error."}, status=500)
        ) from e
