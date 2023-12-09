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
            except Exception as e:
                raise TypeError("Invalid ObjectId") from e
            return v
        raise TypeError("ObjectId required")
