import logging

from bson import ObjectId

from flask import Blueprint, g
from app.base.custom_types import ObjectIdStr
from app.base.utils.query import get_object_or_404
from app.user.auth import Auth
from app.user.models import User

from ..models import Post, Reaction

logger = logging.getLogger(__name__)
router = Blueprint("reactions", __name__, url_prefix="/api/v1")


@router.post("/posts/<string:post_id>/reactions")
@Auth.auth_required
def create_reactions(
    post_id: ObjectIdStr,
):
    user: User = g.user
    post = get_object_or_404(Post, {"_id": ObjectId(post_id)})
    update_result = Reaction.update_one(
        {"post_id": post.id, "$where": "this.user_ids.length < 100"},
        {"$addToSet": {"user_ids": user.id}},
        upsert=True,
    )
    if update_result.upserted_id is not None:
        pass
        # Insert new one
        # update_result.matched_count and update_result.modified_count should be zero
    return {"message": "Reaction Added"}, 200


@router.delete("/posts/<string:post_id>/reactions")
@Auth.auth_required
def delete_post_reactions(
    post_id: ObjectIdStr,
):
    user: User = g.user

    post = get_object_or_404(Post, {"_id": ObjectId(post_id)})
    Reaction.update_one(
        {"post_id": post.id, "user_ids": {"$in": [user.id]}},
        {"$pull": {"user_ids": user.id}},
    )
    return {"message": "Reaction Deleted"}
