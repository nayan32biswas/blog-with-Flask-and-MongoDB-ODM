import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from flask import Blueprint, Response, g, request
from mongodb_odm import ODMObjectId
from slugify import slugify

from app.base.custom_types import ObjectIdStr
from app.base.utils import get_offset, parse_json, update_partially
from app.base.utils.query import get_object_or_404
from app.base.utils.response import ExType, custom_response, http_exception
from app.base.utils.string import rand_slug_str
from app.user.auth import Auth
from app.user.models import User

from ..models import Comment, Post, Reaction, Topic
from ..schemas.posts import (
    PostCreate,
    PostDetailsOut,
    PostListOut,
    PostOut,
    PostUpdate,
    TopicIn,
    TopicOut,
)

logger = logging.getLogger(__name__)
router = Blueprint("posts", __name__, url_prefix="/api/v1")


def create_topic(topic_name: str, user: User) -> Topic:
    topic, created = Topic.get_or_create({"name": topic_name})
    if created:
        topic.update(raw={"$set": {"user_id": user.id}})
        topic.user_id = user.id
    return topic


@router.post("/topics")
@Auth.auth_required
def create_topics() -> Response:
    user: User = g.user
    topic_data = parse_json(TopicIn)

    topic = create_topic(topic_data.name, user)

    return custom_response(TopicOut.from_orm(topic).dict(), 201)


@router.get("/topics")
@Auth.auth_optional
def get_topics() -> Response:
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    q = request.args.get("q")

    offset = get_offset(page, limit)
    filter: Dict[str, Any] = {}
    if q:
        filter["$text"] = {"$search": q}

    topic_qs = Topic.find(filter=filter, limit=limit, skip=offset)
    results = [TopicOut.from_orm(topic).dict() for topic in topic_qs]

    topic_count = Topic.count_documents(filter=filter)

    return custom_response({"count": topic_count, "results": results}, 200)


def get_short_description(description: Optional[str]) -> str:
    if description:
        return description[:200]
    return ""


def get_or_create_post_topics(topics_name: List[str], user: User) -> List[Topic]:
    topics: List[Topic] = []
    for topic_name in topics_name:
        topic = create_topic(topic_name, user)
        if topic:
            topics.append(topic)
    return topics


@router.post("/posts")
@Auth.auth_required
def create_posts() -> Response:
    user: User = g.user
    post_data = parse_json(PostCreate)

    short_description = post_data.short_description

    if not post_data.short_description:
        short_description = get_short_description(post_data.description)

    topics = get_or_create_post_topics(post_data.topics, user)

    if post_data.publish_at and post_data.publish_at < datetime.utcnow():
        raise http_exception(
            status=400,
            detail="Please choose future date.",
            code=ExType.VALIDATION_ERROR,
            field="publish_at",
        )
    if post_data.publish_now:
        post_data.publish_at = datetime.utcnow()

    post = Post(
        author_id=user.id,
        slug=str(ObjectId()),
        title=post_data.title,
        short_description=short_description,
        description=post_data.description,
        cover_image=post_data.cover_image,
        publish_at=post_data.publish_at,
        topic_ids=[topic.id for topic in topics],
    ).create()

    is_slug_saved = False
    slug = slugify(post.title)
    for i in range(1, 10):
        try:
            new_slug = f"{slug}-{rand_slug_str(i)}" if i > 1 else slug
            post.update(raw={"$set": {"slug": new_slug}})
            post.slug = new_slug
            is_slug_saved = True
            break
        except Exception:
            pass
    if is_slug_saved is False:
        post.delete()
        raise http_exception(
            status=400,
            detail="Title error",
            code=ExType.VALIDATION_ERROR,
            field="title",
        )
    post.topics = topics
    return custom_response(PostOut.from_orm(post).dict(), 201)


@router.get("/posts")
@Auth.auth_optional
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
        filter["$text"] = {"$search": q}

    post_qs = Post.find(filter=filter, limit=limit, skip=offset)
    results = [PostListOut.from_orm(post).dict() for post in Post.load_related(post_qs)]

    post_count = Post.count_documents(filter=filter)

    return custom_response({"count": post_count, "results": results}, 200)


@router.get("/posts/<string:slug>")
@Auth.auth_optional
def get_post_details(slug: str) -> Response:
    user = g.user
    filter: Dict[str, Any] = {
        "slug": slug,
        # "publish_at": {"$ne": None, "$lt": datetime.utcnow()},
    }

    try:
        post = Post.get(filter=filter)
        if post.publish_at is None or post.publish_at > datetime.utcnow():
            if user is None or user.id != post.author_id:
                raise http_exception(
                    status=403,
                    code=ExType.PERMISSION_ERROR,
                    detail="You don't have permission to get this object.",
                )
        post.author = User.get({"_id": post.author_id})
    except Exception:
        raise http_exception(
            status=404,
            code=ExType.OBJECT_NOT_FOUND,
            detail="Object not found.",
        )
    post.topics = [
        TopicOut.from_orm(topic)
        for topic in Topic.find({"_id": {"$in": post.topic_ids}})
    ]

    return custom_response(PostDetailsOut.from_orm(post).dict(), 200)


@router.patch("/posts/<string:slug>")
@Auth.auth_required
def update_posts(slug: ObjectIdStr) -> Response:
    post_data = parse_json(PostUpdate)
    user: User = g.user

    post = get_object_or_404(Post, {"slug": slug})

    if post.author_id != user.id:
        raise http_exception(
            status=403,
            code=ExType.PERMISSION_ERROR,
            detail="You don't have access to update this post.",
        )

    if post_data.publish_at and post.publish_at != post_data.publish_at:
        if post_data.publish_at < datetime.utcnow():
            raise http_exception(
                status=400,
                detail="Please choose future date.",
                code=ExType.VALIDATION_ERROR,
                field="publish_at",
            )
    if post_data.publish_now:
        post_data.publish_at = datetime.utcnow()

    post = update_partially(post, post_data)

    post.short_description = post_data.short_description
    if not post.short_description and post_data.description:
        post.short_description = get_short_description(post_data.description)

    if post_data.topics:
        topics = get_or_create_post_topics(post_data.topics, user)
        post.topic_ids = [topic.id for topic in topics]
    post.update()

    return custom_response({"message": "Post Updated"}, 200)


@router.delete("/posts/<string:slug>")
@Auth.auth_required
def delete_post(slug: str) -> Response:
    user: User = g.user

    post: Post = get_object_or_404(Post, {"slug": slug})
    if post.author_id != user.id:
        raise http_exception(
            status=403,
            code=ExType.PERMISSION_ERROR,
            detail="You don't have access to delete this post.",
        )
    Comment.delete_many({"post_id": post.id})
    Reaction.delete_many({"post_id": post.id})
    post.delete()
    return custom_response({"message": "Deleted"}, 200)
