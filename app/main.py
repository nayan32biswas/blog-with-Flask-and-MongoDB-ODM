import logging
from logging.config import dictConfig

from flask import Flask
from mongodb_odm import connect, disconnect

from app.base import config
from app.base.middleware import catch_exceptions_middleware
from app.base.routers import base_api
from app.cli import app as cli_app
from app.post.routers import post_api
from app.user.routers import user_api

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    dictConfig(config.log_config)
    app = Flask(__name__)

    app.config["SECRET_KEY"] = config.SECRET_KEY
    connect(config.MONGO_URL)

    app.register_blueprint(base_api)
    app.register_blueprint(post_api)
    app.register_blueprint(user_api)

    return app


app = create_app()

app.register_error_handler(500, catch_exceptions_middleware)

if __name__ == "__main__":
    print("new connection")
    # connect(config.MONGO_URL)

    # app = create_app()

    cli_app()
    disconnect()
