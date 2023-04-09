import logging
from typing import Any, Dict, TypeVar

from mongodb_odm.exceptions import ObjectDoesNotExist

from app.base.utils.response import http_exception

logger = logging.getLogger(__name__)
T = TypeVar("T")


def get_object_or_404(
    Model: T,
    filter: Dict[str, Any],
    detail: str = "Object Not Found",
    **kwargs: Dict[str, Any],
) -> T:
    try:
        return Model.get(filter, **kwargs)  # type: ignore
    except ObjectDoesNotExist:
        logger.warning(f"404 on:{Model.__name__} filter:{kwargs}")  # type: ignore
        raise http_exception(detail=detail, status=404)
