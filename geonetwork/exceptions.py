from typing import Dict, Any
from requests import Response


class GnException(Exception):
    def __init__(self, code: int, details: Dict[str, Any]):
        super().__init__()
        self.code = code
        self.details = details


class AuthException(GnException):
    pass


class APIVersionException(GnException):
    def __init__(self, details: Dict[str, Any]):
        super().__init__(501, details)


class ParameterException(GnException):
    pass


class TimeoutException(GnException):
    def __init__(self, details: Dict[str, Any]):
        super().__init__(504, details)


def raise_for_status(response: Response):
    if 400 <= response.status_code < 600:
        raise GnException(response.status_code, {"response": response})
