from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.user.schemas import PublicUserListOut


class TopicIn(BaseModel):
    name: str = Field(max_length=127)

    class Config:
        orm_mode = True


class TopicOut(BaseModel):
    name: str

    class Config:
        orm_mode = True


class PostCreate(BaseModel):
    title: str = Field(max_length=255)
    short_description: Optional[str] = Field(max_length=512, default=None)
    cover_image: Optional[str] = None

    publish_at: Optional[datetime] = None
    publish_now: Optional[bool] = None

    description: Optional[str] = None
    topics: List[str] = []

    class Config:
        orm_mode = True


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    short_description: Optional[str] = Field(default=None, max_length=512)
    cover_image: Optional[str] = None

    publish_at: Optional[datetime] = None
    publish_now: Optional[bool] = None

    description: Optional[str] = None
    topics: List[str] = []

    class Config:
        orm_mode = True


class PostOut(BaseModel):
    title: str = Field(max_length=255)
    slug: str = Field(max_length=300)
    short_description: Optional[str] = Field(max_length=512, default=None)
    cover_image: Optional[str] = None

    publish_at: Optional[datetime] = None
    topics: List[TopicOut] = []

    class Config:
        orm_mode = True


class PostListOut(BaseModel):
    author: Optional[PublicUserListOut] = None
    title: str = Field(max_length=255)
    slug: str = Field(max_length=300)
    short_description: Optional[str] = Field(max_length=512, default=None)
    cover_image: Optional[str] = None
    total_comment: int = Field(default=0)
    total_reaction: int = Field(default=0)

    publish_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class PostDetailsOut(BaseModel):
    author: Optional[PublicUserListOut] = None
    slug: str = Field(max_length=300)
    title: str = Field(max_length=255)
    short_description: Optional[str] = Field(max_length=512, default=None)
    cover_image: Optional[str] = None
    total_comment: int = Field(default=0)
    total_reaction: int = Field(default=0)

    publish_at: Optional[datetime] = None

    description: Optional[str] = None
    topics: List[TopicOut] = []

    class Config:
        orm_mode = True
