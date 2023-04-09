from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.base.custom_types import ObjectIdStr
from app.user.schemas import PublicUserListOut


class CommentIn(BaseModel):
    description: str


class ReplyIn(BaseModel):
    description: str


class ReplyOut(BaseModel):
    id: ObjectIdStr
    user: Optional[PublicUserListOut]
    description: str

    created_at: datetime
    updated_at: datetime


class CommentOut(BaseModel):
    id: ObjectIdStr
    user: Optional[PublicUserListOut]

    description: str
    replies: List[ReplyOut] = []

    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
