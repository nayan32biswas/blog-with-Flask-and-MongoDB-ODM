import logging
from typing import Any

from flask import Blueprint, Response, g
from mongodb_odm import ODMObjectId

from app.base.utils.query import get_object_or_404
from app.base.utils.response import custom_response
from app.user.auth import Auth
from app.user.models import User

from ..models import Post, Reaction

logger = logging.getLogger(__name__)
router = Blueprint("reactions", __name__, url_prefix="/api/v1")


def update_total_reaction(post_id: Any, val: int) -> None:
    Post.update_one({"_id": ODMObjectId(post_id)}, {"$inc": {"total_reaction": val}})


@router.post("/posts/<string:slug>/reactions")
@Auth.auth_required
def create_reactions(slug: str) -> Response:
    user: User = g.user

    post = get_object_or_404(Post, {"slug": slug})
    update_result = Reaction.update_one(
        {"post_id": post.id, "$where": "this.user_ids.length < 100"},
        {"$addToSet": {"user_ids": user.id}},
        upsert=True,
    )
    if update_result.upserted_id is not None:
        pass
        # Insert new one
        # update_result.matched_count and update_result.modified_count should be zero

    if update_result.modified_count or update_result.upserted_id is not None:
        # increase total comment for post
        update_total_reaction(post.id, 1)
        message = "Reaction Added"
    else:
        message = "You already have an reaction in this post"

    return custom_response({"message": message}, 201)


@router.delete("/posts/<string:slug>/reactions")
@Auth.auth_required
def delete_post_reactions(slug: str) -> Response:
    user: User = g.user

    post = get_object_or_404(Post, {"slug": slug})
    update_result = Reaction.update_one(
        {"post_id": post.id, "user_ids": user.id},
        {"$pull": {"user_ids": user.id}},
    )
    if update_result.modified_count:
        # decrease total comment for post
        update_total_reaction(post.id, -1)

    return custom_response({"message": "Reaction Deleted"}, 200)
