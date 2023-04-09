import logging
import os
from pathlib import Path

from .config_utils import comma_separated_str_to_list

logger = logging.getLogger(__name__)

DEBUG = bool(os.environ.get("DEBUG", False))
SECRET_KEY = os.environ.get("SECRET_KEY", "long-long-long-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", 7))

MONGO_URL = str(os.environ.get("MONGO_URL"))

ALLOWED_HOSTS = comma_separated_str_to_list(os.environ.get("ALLOWED_HOSTS", "*"))
SITE_URL = os.environ.get("SITE_URL")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
STATIC_ROOT = os.path.join(BASE_DIR, "static")


LOG_LEVEL = "INFO" if DEBUG is True else "INFO"

log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] - [%(name)s] - [%(levelname)s] - %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": LOG_LEVEL,
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "blog": {"handlers": ["console"], "level": LOG_LEVEL},
    },
    "root": {"level": LOG_LEVEL, "handlers": ["console"]},
}

"""
Logging Level
logger.debug        -> 10
logger.info         -> 20
logger.warning      -> 30
logger.error        -> 40
logger.critical     -> 50
"""
