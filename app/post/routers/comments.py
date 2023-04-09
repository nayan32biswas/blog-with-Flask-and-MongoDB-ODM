import logging

from flask import Blueprint, Response, g, request
from mongodb_odm import ODMObjectId

from app.base.custom_types import ObjectIdStr
from app.base.utils import get_offset, parse_json
from app.base.utils.query import get_object_or_404
from app.base.utils.response import custom_response, http_exception
from app.user.auth import Auth
from app.user.models import User

from ..models import Comment, EmbeddedReply
from ..schemas.comments import CommentIn, CommentOut, ReplyIn, ReplyOut

logger = logging.getLogger(__name__)
router = Blueprint("comments", __name__, url_prefix="/api/v1")


@router.post("/posts/<string:post_id>/comments")
@Auth.auth_required
def create_comments(post_id: ObjectIdStr) -> Response:
    user: User = g.user
    comment_data = parse_json(CommentIn)

    comment = Comment(
        user_id=user.id,
        post_id=ODMObjectId(post_id),
        description=comment_data.description,
    ).create()

    comment.user = user
    return custom_response(CommentOut.from_orm(comment).dict(), 201)


@router.get("/posts/<string:post_id>/comments")
@Auth.auth_optional
def get_comments(post_id: ObjectIdStr) -> Response:
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))

    offset = get_offset(page, limit)

    filter = {"post_id": ODMObjectId(post_id)}

    comment_qs = Comment.find(filter, skip=offset)
    # Load related user only
    comments = Comment.load_related(comment_qs, fields=["user"])

    user_ids = list(
        set(replies.user_id for comment in comments for replies in comment.replies)
    )
    users_dict = {user.id: user for user in User.find({"_id": {"$in": user_ids}})}

    results = []
    for comment in comments:
        comment_dict = comment.dict()
        for reply in comment_dict["replies"]:
            # Assign child replies
            reply["user"] = users_dict.get(reply["user_id"])
        results.append(CommentOut(**comment_dict).dict())

    comment_count = Comment.count_documents(filter)

    return custom_response({"count": comment_count, "results": results}, 200)


@router.put("/posts/<string:post_id>/comments/<string:comment_id>")
@Auth.auth_required
def update_comments(post_id: ObjectIdStr, comment_id: ObjectIdStr) -> Response:
    user: User = g.user

    comment_data = parse_json(CommentIn)
    comment = get_object_or_404(
        Comment,
        {
            "_id": ODMObjectId(comment_id),
            "post_id": ODMObjectId(post_id),
        },
    )
    if comment.user_id != user.id:
        raise http_exception(
            detail="You don't have access to update this comment.",
            status=403,
        )

    comment.description = comment_data.description
    comment.update()
    comment.user = user

    return custom_response(CommentOut.from_orm(comment).dict(), 200)


@router.delete("/posts/<string:post_id>/comments/<string:comment_id>")
@Auth.auth_required
def delete_comments(post_id: ObjectIdStr, comment_id: ObjectIdStr) -> Response:
    user: User = g.user
    comment = get_object_or_404(
        Comment,
        {"_id": ODMObjectId(comment_id), "post_id": ODMObjectId(post_id)},
    )
    if comment.user_id != user.id:
        raise http_exception(
            detail="You don't have access to delete this comment.", status=403
        )
    comment.delete()

    return custom_response({"message": "Deleted"}, 200)


@router.post(
    "/posts/<string:post_id>/comments/<string:comment_id>/replies",
)
@Auth.auth_required
def create_replies(post_id: ObjectIdStr, comment_id: ObjectIdStr) -> Response:
    user: User = g.user
    reply_data = parse_json(ReplyIn)
    comment = get_object_or_404(
        Comment,
        {
            "_id": ODMObjectId(comment_id),
            "post_id": ODMObjectId(post_id),
        },
    )
    if len(comment.replies) >= 100:
        raise http_exception(
            detail="Comment should have less then 100 comment.",
            status=400,
        )
    reply_dict = EmbeddedReply(
        id=ODMObjectId(), user_id=user.id, description=reply_data.description
    ).dict()
    comment.update(raw={"$push": {"replies": reply_dict}})

    reply_dict["user"] = user.dict()

    return custom_response(ReplyOut(**reply_dict).dict(), 201)


@router.put(
    "/posts/<string:post_id>/comments/<string:comment_id>/replies/<string:reply_id>",
)
@Auth.auth_required
def update_replies(
    post_id: ObjectIdStr, comment_id: ObjectIdStr, reply_id: ObjectIdStr
) -> Response:
    user: User = g.user
    reply_data = parse_json(ReplyIn)
    r_id = ODMObjectId(reply_id)
    update_comment = Comment.update_one(
        {
            "_id": ODMObjectId(comment_id),
            "post_id": ODMObjectId(post_id),
            "replies.id": r_id,
            "replies.user_id": user.id,
        },
        {"$set": {"replies.$[reply].description": reply_data.description}},
        array_filters=[{"reply.id": r_id}],
    )

    if update_comment.modified_count != 1:
        raise http_exception(
            detail="You don't have permission to update this replies",
            status=403,
        )
    return custom_response({"message": "Updated"}, 200)


@router.delete(
    "/posts/<string:post_id>/comments/<string:comment_id>/replies/<string:reply_id>",
)
@Auth.auth_required
def delete_replies(
    post_id: ObjectIdStr, comment_id: ObjectIdStr, reply_id: ObjectIdStr
) -> Response:
    user: User = g.user

    r_id = ODMObjectId(reply_id)
    update_comment = Comment.update_one(
        {
            "_id": ODMObjectId(comment_id),
            "post_id": ODMObjectId(post_id),
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
            detail="You don't have permission to delete this replies", status=403
        )

    return custom_response({"message": "Deleted"}, 200)
