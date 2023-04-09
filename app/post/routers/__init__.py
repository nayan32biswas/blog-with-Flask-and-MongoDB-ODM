from flask import Blueprint

from . import comments, posts, reactions

post_api = Blueprint("post", __name__, url_prefix="/")

post_api.register_blueprint(posts.router)
post_api.register_blueprint(comments.router)
post_api.register_blueprint(reactions.router)
