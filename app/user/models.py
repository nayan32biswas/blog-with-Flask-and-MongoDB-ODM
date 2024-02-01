from datetime import datetime
from typing import Optional
from uuid import uuid4

from mongodb_odm import ASCENDING, Document, Field, IndexModel


class User(Document):
    username: str = Field(...)
    full_name: str = Field(...)
    image: Optional[str] = Field(default=None)

    is_active: bool = True
    joining_date: datetime
    last_login: Optional[datetime] = None

    password: Optional[str] = Field(default=None)
    # random_str will be used to log out from all devices.
    random_str: Optional[str] = Field(default=None, max_length=64)

    updated_at: datetime = Field(default_factory=datetime.now)

    class ODMConfig(Document.ODMConfig):
        collection_name = "user"
        indexes = [
            IndexModel([("username", ASCENDING)], unique=True),
        ]

    @classmethod
    def new_random_str(cls) -> str:
        return str(uuid4())
