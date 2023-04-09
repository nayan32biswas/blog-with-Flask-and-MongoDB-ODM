import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from flask import Blueprint, request, g

from bson import ObjectId
from mongodb_odm import ODMObjectId

from app.base.custom_types import ObjectIdStr
from app.base.utils import get_offset, parse_json, update_partially
from app.base.utils.query import get_object_or_404
from app.base.utils.response import http_exception
from app.user.auth import Auth
from app.user.models import User

from ..models import Post, Tag
from ..schemas.posts import (
    PostCreate,
    PostDetailsOut,
    PostListOut,
    PostUpdate,
    TagIn,
    TagOut,
)


logger = logging.getLogger(__name__)
router = Blueprint("posts", __name__, url_prefix="/api/v1")


@router.post("/tags")
@Auth.auth_required
def create_tags():
    user: User = g.user

    tag_data = parse_json(TagIn)

    name = tag_data.name.lower()
    tag, created = Tag.get_or_create({"name": name})

    if created:
        if user:
            tag.user_id = user.id
        tag.update()

    return TagOut.from_orm(tag).dict(), 201


@router.get("/tags")
@Auth.auth_optional
def get_tags():
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    q = request.args.get("q")

    offset = get_offset(page, limit)
    filter: Dict[str, Any] = {}
    if q:
        filter["name"] = re.compile(q, re.IGNORECASE)

    tag_qs = Tag.find(filter=filter, limit=limit, skip=offset)
    results = [TagOut.from_orm(tag).dict() for tag in tag_qs]

    tag_count = Tag.count_documents(filter=filter)

    return {"count": tag_count, "results": results}


def get_short_description(description: Optional[str]) -> str:
    if description:
        return description[:200]
    return ""


@router.post("/posts")
@Auth.auth_required
def create_posts():
    user: User = g.user
    post_data = parse_json(PostCreate)

    short_description = post_data.short_description
    if not post_data.short_description:
        short_description = get_short_description(post_data.description)

    post = Post(
        author_id=user.id,
        title=post_data.title,
        short_description=short_description,
        description=post_data.description,
        cover_image=post_data.cover_image,
        publish_at=post_data.publish_at,
        tag_ids=[ODMObjectId(id) for id in post_data.tag_ids],
    ).create()

    post.author = user
    post.tags = [
        TagOut.from_orm(tag) for tag in Tag.find({"_id": {"$in": post.tag_ids}})
    ]

    return PostDetailsOut.from_orm(post).dict(), 201


@router.get("/posts")
def get_posts():
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    q = request.args.get("q")
    tags = request.args.getlist("tags")
    author_id = request.args.get("author_id")

    offset = get_offset(page, limit)
    filter: Dict[str, Any] = {
        "publish_at": {"$ne": None, "$lt": datetime.utcnow()},
    }
    if author_id:
        filter["author_id"] = ObjectId(author_id)
    if tags:
        filter["tag_ids"] = {"$in": [ODMObjectId(id) for id in tags]}
    if q:
        filter["title"] = q

    post_qs = Post.find(filter=filter, limit=limit, skip=offset)
    results = [PostListOut.from_orm(post).dict() for post in Post.load_related(post_qs)]

    post_count = Post.count_documents(filter=filter)

    return {"count": post_count, "results": results}


@router.get("/posts/<string:post_id>")
def get_post_details(post_id):
    filter: Dict[str, Any] = {
        "_id": ObjectId(post_id),
        "publish_at": {"$ne": None, "$lt": datetime.utcnow()},
    }
    try:
        post = Post.get(filter=filter)
        post.author = User.get({"_id": post.author_id})
    except Exception:
        raise http_exception(detail="Object not found.", status=400)
    post.tags = [
        TagOut.from_orm(tag) for tag in Tag.find({"_id": {"$in": post.tag_ids}})
    ]

    return PostDetailsOut.from_orm(post).dict(), 200


@router.patch("/posts/<string:post_id>")
@Auth.auth_required
def update_posts(post_id):
    post_data = parse_json(PostUpdate)
    user: User = g.user

    post = get_object_or_404(Post, {"_id": ObjectId(post_id)})

    if post.author_id != user.id:
        raise http_exception(
            detail="You don't have access to update this post.", status=403
        )

    post = update_partially(post, post_data)

    post.short_description = post_data.short_description
    if not post.short_description and post_data.description:
        post.short_description = get_short_description(post_data.description)
    post.update()

    post.author = user

    return PostDetailsOut.from_orm(post).dict(), 200


@router.delete("/posts/<string:post_id>")
@Auth.auth_required
def delete_post(post_id: ObjectIdStr):
    post = get_object_or_404(Post, {"_id": ObjectId(post_id)})
    user: User = g.user

    if post.author_id != user.id:
        raise http_exception(
            detail="You don't have access to delete this post.", status=403
        )
    post.delete()
    return {"message": "Deleted"}, 200
