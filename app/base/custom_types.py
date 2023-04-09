from typing import Any, Union

from bson import ObjectId


class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls) -> Any:
        yield cls.validate

    @classmethod
    def validate(cls, v: Union[str, ObjectId]) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        elif isinstance(v, str):
            try:
                ObjectId(v)
            except Exception:
                raise TypeError("Invalid ObjectId")
            return v
        raise TypeError("ObjectId required")
