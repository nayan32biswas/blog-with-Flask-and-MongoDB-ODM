import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from flask import Blueprint, Response, g, request
from mongodb_odm import ObjectIdStr, ODMObjectId
from slugify import slugify

from app.base.utils import parse_json, update_partially
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


def get_or_create_topic(
    topic_name: str, user: Optional[User] = None
) -> Tuple[Topic, bool]:
    user_id = user.id if user else None
    try:
        topic = Topic.get({"name": topic_name})
        return topic, False
    except Exception:
        pass
    slug = slugify(topic_name)
    for i in range(3, 20):
        try:
            return (
                Topic(
                    name=topic_name,
                    slug=f"{slug}-{rand_slug_str(i)}",
                    user_id=user_id,
                ).create(),
                True,
            )
        except Exception:
            pass
    raise Exception("Unable to create the Topic")


@router.post("/topics")
@Auth.auth_required
def create_topics() -> Response:
    user: User = g.user
    topic_data = parse_json(TopicIn)

    topic, _ = get_or_create_topic(topic_name=topic_data.name, user=user)

    return custom_response(TopicOut(**topic.model_dump()).model_dump(), 201)


@router.get("/topics")
@Auth.auth_optional
def get_topics() -> Response:
    after: Optional[str] = request.args.get("after", None)
    limit = int(request.args.get("limit", 20))
    q = request.args.get("q")

    filter: Dict[str, Any] = {}
    if q:
        filter["$text"] = {"$search": q}
    if after:
        filter["_id"] = {"$lt": ObjectId(after)}

    sort = [("_id", -1)]

    results = []
    next_cursor = None
    topic_qs = Topic.find(filter=filter, sort=sort, limit=limit)
    for topic in topic_qs:
        next_cursor = topic.id
        results.append(TopicOut(**topic.model_dump()).model_dump())

    next_cursor = next_cursor if len(results) == limit else None

    return custom_response({"after": ObjectIdStr(next_cursor), "results": results}, 200)


def get_short_description(description: Optional[str]) -> str:
    if description:
        return description[:200]
    return ""


def get_or_create_post_topics(topics_name: List[str], user: User) -> List[Topic]:
    topics: List[Topic] = []
    for topic_name in topics_name:
        topic, _ = get_or_create_topic(topic_name=topic_name, user=user)
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

    if post_data.publish_at and post_data.publish_at < datetime.now():
        raise http_exception(
            status=400,
            detail="Please choose future date.",
            code=ExType.VALIDATION_ERROR,
            field="publish_at",
        )
    if post_data.publish_now:
        post_data.publish_at = datetime.now()

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
    return custom_response(PostOut(**post.model_dump()).model_dump(), 201)


@router.get("/posts")
@Auth.auth_optional
def get_posts() -> Response:
    user = g.user

    after: Optional[str] = request.args.get("after", None)
    limit = int(request.args.get("limit", 20))
    q = request.args.get("q")
    topics = request.args.getlist("topics")
    username = request.args.get("username")

    filter: Dict[str, Any] = {
        "publish_at": {"$ne": None, "$lt": datetime.now()},
    }
    if username:
        if user and user.username == username:
            filter["author_id"] = user.id
            filter.pop("publish_at")
        else:
            user = User.get({"username": username})
            filter["author_id"] = user.id
    if topics:
        topic_ids = [
            ODMObjectId(obj["_id"])
            for obj in Topic.find_raw({"slug": {"$in": topics}}, projection={"slug": 1})
        ]
        filter["topic_ids"] = {"$in": topic_ids}
    if q:
        filter["$text"] = {"$search": q}
    if after:
        filter["_id"] = {"$lt": ObjectId(after)}

    sort = [("_id", -1)]

    post_qs = Post.find(
        filter=filter,
        sort=sort,
        limit=limit,
        projection={"description": 0},
    )
    results = []
    next_cursor = None
    for post in Post.load_related(post_qs):
        next_cursor = post.id
        results.append(PostListOut(**post.model_dump()).model_dump())

    next_cursor = next_cursor if len(results) == limit else None

    return custom_response({"after": ObjectIdStr(next_cursor), "results": results}, 200)


@router.get("/posts/<string:slug>")
@Auth.auth_optional
def get_post_details(slug: str) -> Response:
    user = g.user
    filter: Dict[str, Any] = {
        "slug": slug,
        # "publish_at": {"$ne": None, "$lt": datetime.now()},
    }

    try:
        post = Post.get(filter=filter)
        if post.publish_at is None or post.publish_at > datetime.now():
            if user is None or user.id != post.author_id:
                raise http_exception(
                    status=403,
                    code=ExType.PERMISSION_ERROR,
                    detail="You don't have permission to get this object.",
                )
        post.author = User.get({"_id": post.author_id})
    except Exception as e:
        raise http_exception(
            status=404,
            code=ExType.OBJECT_NOT_FOUND,
            detail="Object not found.",
        ) from e
    post.topics = [
        TopicOut(**topic.model_dump())
        for topic in Topic.find({"_id": {"$in": post.topic_ids}})
    ]

    return custom_response(PostDetailsOut(**post.model_dump()).model_dump(), 200)


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
        if post_data.publish_at < datetime.now():
            raise http_exception(
                status=400,
                detail="Please choose future date.",
                code=ExType.VALIDATION_ERROR,
                field="publish_at",
            )
    if post_data.publish_now:
        post_data.publish_at = datetime.now()

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
