from datetime import datetime
from typing import List, Optional

from mongodb_odm import ObjectIdStr
from pydantic import BaseModel

from app.user.schemas import PublicUserListOut


class CommentIn(BaseModel):
    description: str


class ReplyIn(BaseModel):
    description: str


class ReplyOut(BaseModel):
    id: ObjectIdStr
    user: Optional[PublicUserListOut] = None
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
