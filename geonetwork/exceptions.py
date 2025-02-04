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


class TimeoutException(GnException):
    def __init__(self, *args, **kwargs):
        super().__init__(504, *args, **kwargs)


def raise_for_status(response: Response):
    if 400 <= response.status_code < 600:
        raise GnException(
            response.status_code,
            GnDetail("HTTP error in GN api"),
            response.request,
            response
        )
