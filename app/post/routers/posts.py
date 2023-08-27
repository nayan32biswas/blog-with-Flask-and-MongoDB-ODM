import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId
from flask import Blueprint, Response, g, request
from mongodb_odm import ODMObjectId

from app.base.custom_types import ObjectIdStr
from app.base.utils import get_offset, parse_json, update_partially
from app.base.utils.query import get_object_or_404
from app.base.utils.response import ExType, custom_response, http_exception
from app.user.auth import Auth
from app.user.models import User

from ..models import Post, Topic
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


@router.post("/topics")
@Auth.auth_required
def create_topics() -> Response:
    user: User = g.user

    topic_data = parse_json(TagIn)

    name = topic_data.name.lower()
    topic, created = Topic.get_or_create({"name": name})

    if created:
        if user:
            topic.user_id = user.id
        topic.update()

    return custom_response(TagOut.from_orm(topic).dict(), 201)


@router.get("/topics")
@Auth.auth_optional
def get_topics() -> Response:
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    q = request.args.get("q")

    offset = get_offset(page, limit)
    filter: Dict[str, Any] = {}
    if q:
        filter["name"] = re.compile(q, re.IGNORECASE)

    topic_qs = Topic.find(filter=filter, limit=limit, skip=offset)
    results = [TagOut.from_orm(topic).dict() for topic in topic_qs]

    topic_count = Topic.count_documents(filter=filter)

    return custom_response({"count": topic_count, "results": results}, 200)


def get_short_description(description: Optional[str]) -> str:
    if description:
        return description[:200]
    return ""


@router.post("/posts")
@Auth.auth_required
def create_posts() -> Response:
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
        topic_ids=[ODMObjectId(id) for id in post_data.topic_ids],
    ).create()

    post.author = user
    post.topics = [
        TagOut.from_orm(topic) for topic in Topic.find({"_id": {"$in": post.topic_ids}})
    ]

    return custom_response(PostDetailsOut.from_orm(post).dict(), 201)


@router.get("/posts")
def get_posts() -> Response:
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    q = request.args.get("q")
    topics = request.args.getlist("topics")
    author_id = request.args.get("author_id")

    offset = get_offset(page, limit)
    filter: Dict[str, Any] = {
        "publish_at": {"$ne": None, "$lt": datetime.utcnow()},
    }
    if author_id:
        filter["author_id"] = ObjectId(author_id)
    if topics:
        filter["topic_ids"] = {"$in": [ODMObjectId(id) for id in topics]}
    if q:
        filter["title"] = q

    post_qs = Post.find(filter=filter, limit=limit, skip=offset)
    results = [PostListOut.from_orm(post).dict() for post in Post.load_related(post_qs)]

    post_count = Post.count_documents(filter=filter)

    return custom_response({"count": post_count, "results": results}, 200)


@router.get("/posts/<string:post_id>")
def get_post_details(post_id: ObjectIdStr) -> Response:
    filter: Dict[str, Any] = {
        "_id": ObjectId(post_id),
        "publish_at": {"$ne": None, "$lt": datetime.utcnow()},
    }
    try:
        post = Post.get(filter=filter)
        post.author = User.get({"_id": post.author_id})
    except Exception:
        raise http_exception(
            status=400, code=ExType.OBJECT_NOT_FOUND, detail="Object not found."
        )
    post.topics = [
        TagOut.from_orm(topic) for topic in Topic.find({"_id": {"$in": post.topic_ids}})
    ]

    return custom_response(PostDetailsOut.from_orm(post).dict(), 200)


@router.patch("/posts/<string:post_id>")
@Auth.auth_required
def update_posts(post_id: ObjectIdStr) -> Response:
    post_data = parse_json(PostUpdate)
    user: User = g.user

    post: Post = get_object_or_404(Post, {"_id": ObjectId(post_id)})

    if post.author_id != user.id:
        raise http_exception(
            status=403,
            code=ExType.PERMISSION_ERROR,
            detail="You don't have access to update this post.",
        )

    updated_post: Post = update_partially(post, post_data)

    updated_post.short_description = post_data.short_description
    if not updated_post.short_description and post_data.description:
        updated_post.short_description = get_short_description(post_data.description)
    updated_post.update()

    updated_post.author = user

    return custom_response(PostDetailsOut.from_orm(updated_post).dict(), 200)


@router.delete("/posts/<string:post_id>")
@Auth.auth_required
def delete_post(post_id: ObjectIdStr) -> Response:
    post: Post = get_object_or_404(Post, {"_id": ObjectId(post_id)})
    user: User = g.user

    if post.author_id != user.id:
        raise http_exception(
            status=403,
            code=ExType.PERMISSION_ERROR,
            detail="You don't have access to delete this post.",
        )
    post.delete()
    return custom_response({"message": "Deleted"}, 200)
