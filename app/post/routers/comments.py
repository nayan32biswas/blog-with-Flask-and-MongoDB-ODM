import logging
from typing import Any, Optional

from bson import ObjectId
from flask import Blueprint, Response, g, request
from mongodb_odm import ObjectIdStr, ODMObjectId

from app.base.utils import parse_json
from app.base.utils.query import get_object_or_404
from app.base.utils.response import ExType, custom_response, http_exception
from app.user.auth import Auth
from app.user.models import User

from ..models import Comment, EmbeddedReply, Post
from ..schemas.comments import CommentIn, CommentOut, ReplyIn, ReplyOut

logger = logging.getLogger(__name__)
router = Blueprint("comments", __name__, url_prefix="/api/v1")


def update_total_comment(post_id: Any, val: int) -> None:
    Post.update_one({"_id": ODMObjectId(post_id)}, {"$inc": {"total_comment": val}})


@router.post("/posts/<string:slug>/comments")
@Auth.auth_required
def create_comments(slug: str) -> Response:
    user: User = g.user
    comment_data = parse_json(CommentIn)

    post = get_object_or_404(Post, filter={"slug": slug})
    comment = Comment(
        user_id=user.id,
        post_id=post.id,
        description=comment_data.description,
    ).create()
    # increase total comment for post
    update_total_comment(post.id, 1)

    comment.user = user

    return custom_response(CommentOut(**comment.model_dump()).model_dump(), 201)


@router.get("/posts/<string:slug>/comments")
@Auth.auth_optional
def get_comments(slug: str) -> Response:
    after: Optional[str] = request.args.get("after", None)
    limit = int(request.args.get("limit", 20))

    post = get_object_or_404(Post, filter={"slug": slug})
    filter = {"post_id": post.id}
    if after:
        filter["_id"] = {"$lt": ObjectId(after)}

    comment_qs = Comment.find(filter, sort=(("_id", -1),), limit=limit)
    # Load related user only
    comments = Comment.load_related(comment_qs, fields=["user"])

    user_ids = list(
        {replies.user_id for comment in comments for replies in comment.replies}
    )
    users_dict = {user.id: user for user in User.find({"_id": {"$in": user_ids}})}

    results = []
    next_cursor = None
    for comment in comments:
        next_cursor = comment.id
        comment_dict = comment.model_dump()
        for reply in comment_dict["replies"]:
            # Assign child replies
            reply["user"] = users_dict.get(reply["user_id"])
        results.append(CommentOut(**comment_dict).model_dump())

    next_cursor = next_cursor if len(results) == limit else None

    return custom_response({"after": ObjectIdStr(next_cursor), "results": results}, 200)


@router.put("/posts/<string:slug>/comments/<string:comment_id>")
@Auth.auth_required
def update_comments(slug: str, comment_id: ObjectIdStr) -> Response:
    user: User = g.user
    comment_data = parse_json(CommentIn)

    post = get_object_or_404(Post, filter={"slug": slug})
    comment = get_object_or_404(
        Comment,
        {
            "_id": ODMObjectId(comment_id),
            "post_id": post.id,
        },
    )
    if comment.user_id != user.id:
        raise http_exception(
            status=403,
            code=ExType.PERMISSION_ERROR,
            detail="You don't have access to update this comment.",
        )

    comment.description = comment_data.description
    comment.update()

    return custom_response({"message": "Comment Updated"}, 200)


@router.delete("/posts/<string:slug>/comments/<string:comment_id>")
@Auth.auth_required
def delete_comments(slug: str, comment_id: ObjectIdStr) -> Response:
    user: User = g.user

    post = get_object_or_404(Post, filter={"slug": slug})
    comment = get_object_or_404(
        Comment,
        {"_id": ODMObjectId(comment_id), "post_id": post.id},
    )
    if comment.user_id != user.id:
        raise http_exception(
            status=403,
            code=ExType.PERMISSION_ERROR,
            detail="You don't have access to delete this comment.",
        )

    comment.delete()
    # decrease total comment for post
    update_total_comment(post.id, -1)

    return custom_response({"message": "Deleted"}, 200)


@router.post(
    "/posts/<string:slug>/comments/<string:comment_id>/replies",
)
@Auth.auth_required
def create_replies(slug: str, comment_id: ObjectIdStr) -> Response:
    user: User = g.user
    reply_data = parse_json(ReplyIn)

    post = get_object_or_404(Post, filter={"slug": slug})
    comment = get_object_or_404(
        Comment,
        {
            "_id": ODMObjectId(comment_id),
            "post_id": post.id,
        },
    )
    if len(comment.replies) >= 100:
        raise http_exception(
            status=400,
            code=ExType.VALIDATION_ERROR,
            detail="Comment should have less then 100 comment.",
        )

    reply_dict = EmbeddedReply(
        id=ODMObjectId(), user_id=user.id, description=reply_data.description
    ).model_dump()
    comment.update(raw={"$push": {"replies": reply_dict}})

    reply_dict["user"] = user.model_dump()
    reply_out = ReplyOut(**reply_dict)

    return custom_response(reply_out.model_dump(), 201)


@router.put(
    "/posts/<string:slug>/comments/<string:comment_id>/replies/<string:reply_id>",
)
@Auth.auth_required
def update_replies(
    slug: str, comment_id: ObjectIdStr, reply_id: ObjectIdStr
) -> Response:
    user: User = g.user
    reply_data = parse_json(ReplyIn)

    post = get_object_or_404(Post, filter={"slug": slug})
    r_id = ODMObjectId(reply_id)
    update_comment = Comment.update_one(
        {
            "_id": ODMObjectId(comment_id),
            "post_id": post.id,
            "replies.id": r_id,
            "replies.user_id": user.id,
        },
        {"$set": {"replies.$[reply].description": reply_data.description}},
        array_filters=[{"reply.id": r_id}],
    )

    if update_comment.modified_count != 1:
        raise http_exception(
            status=403,
            code=ExType.PERMISSION_ERROR,
            detail="You don't have permission to update this replies",
        )

    return custom_response({"message": "Updated"}, 200)


@router.delete(
    "/posts/<string:slug>/comments/<string:comment_id>/replies/<string:reply_id>",
)
@Auth.auth_required
def delete_replies(
    slug: str, comment_id: ObjectIdStr, reply_id: ObjectIdStr
) -> Response:
    user: User = g.user

    post = get_object_or_404(Post, filter={"slug": slug})
    r_id = ODMObjectId(reply_id)
    update_comment = Comment.update_one(
        {
            "_id": ODMObjectId(comment_id),
            "post_id": post.id,
            "replies": {
                "$elemMatch": {
                    "id": r_id,
                    "user_id": user.id,
                }
            },
        },
        {
            "$pull": {
                "replies": {
                    "id": r_id,
                    "user_id": user.id,
                },
            }
        },
    )
    if update_comment.modified_count != 1:
        raise http_exception(
            status=403,
            code=ExType.PERMISSION_ERROR,
            detail="You don't have permission to delete this replies",
        )

    return custom_response({"message": "Deleted"}, 200)
