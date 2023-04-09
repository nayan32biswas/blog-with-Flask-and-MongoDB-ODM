import re
import string
from base64 import b64encode
from random import choice
from typing import Any


def rand_str(N: int = 12) -> str:
    return "".join(
        choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)
        for _ in range(N)
    )


def str_to_regex(s: str) -> Any:
    return re.compile(re.escape(s))


def str_to_regex_insensitive(s: str) -> Any:
    return re.compile(re.escape(s), re.IGNORECASE)


def base64(s: str) -> str:
    """Encode the string s using Base64."""
    b: bytes = s.encode("utf-8") if isinstance(s, str) else s
    return b64encode(b).decode("ascii")


# def un_base64(s: str) -> str:
#     """Decode the string s using Base64."""
#     try:
#         b: bytes = s.encode("ascii") if isinstance(s, str) else s
#     except UnicodeEncodeError:
#         return ""
#     try:
#         return b64decode(b).decode("utf-8")
#     except (binascii.Error, UnicodeDecodeError):
#         return ""
