import html
import json
from typing import Dict, Any
from requests import Request, Response
from dataclasses import dataclass, field


@dataclass
class GnDetail:
    message: str
    info: Dict[str, Any] = field(default_factory=lambda: {})


class GnException(Exception):
    def __init__(
            self,
            code: int,
            detail: GnDetail,
            parent_request: Request = None,
            parent_response: Response = None
    ):
        super().__init__()
        self.code = code
        self.detail = detail
        self.parent_request = parent_request
        self.parent_response = parent_response


class AuthException(GnException):
    pass


class APIVersionException(GnException):
    def __init__(self, *args, **kwargs):
        super().__init__(501, *args, **kwargs)


class ParameterException(GnException):
    pass


class GnElasticException(GnException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.detail.info = format_ES_error(self.parent_response.json())


class GnRequestException(GnException):
    pass


def format_ES_error(error: Dict[str, str]) -> Dict[str, Any]:
    error_lines = html.unescape(error.get("message", "")).split("\n")
    result_dict = {}
    i = 0
    while i < len(error_lines):
        try:
            result_dict[error_lines[i]] = json.loads(error_lines[i + 1].rstrip("."))
            i += 2
        except Exception:
            if error_lines[i] != ".":
                result_dict[f"info_{i}"] = error_lines[i]
            i += 1
    return result_dict


def raise_for_status(response: Response, exception_class=GnException):
    if 400 <= response.status_code < 600:
        raise exception_class(
            response.status_code,
            GnDetail("HTTP error in GN api"),
            response.request,
            response
        )
