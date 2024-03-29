import logging
from typing import Any, Dict, no_type_check

from mongodb_odm.exceptions import ObjectDoesNotExist

from app.base.utils.response import ExType, http_exception

logger = logging.getLogger(__name__)


@no_type_check
def get_object_or_404(
    Model,
    filter: Dict[str, Any],
    detail: str = "Object Not Found",
    **kwargs: Dict[str, Any],
):
    try:
        return Model.get(filter, **kwargs)
    except ObjectDoesNotExist as e:
        logger.warning(f"404 on:{Model.__name__} filter:{kwargs}")
        raise http_exception(
            status=404,
            code=ExType.OBJECT_NOT_FOUND,
            detail=detail,
        ) from e
