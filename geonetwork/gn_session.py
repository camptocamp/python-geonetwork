import logging
import requests
from requests.exceptions import ConnectTimeout, ConnectionError, HTTPError
from typing import Union, Dict, Any
from collections import namedtuple
from .exceptions import AuthException, TimeoutException


Credentials = namedtuple("Credentials", ["login", "password"])


logger = logging.getLogger("GN Session")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "{asctime} - {name}:{levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
    )
)
logger.addHandler(handler)


class GnSession(requests.Session):
    def __init__(self, credentials: Union[Credentials, None] = None, verifytls: bool = True):
        self.credentials = credentials
        self.verifytls = verifytls
        self.base_headers: Dict[str, str] = {}
        super().__init__()

    def set_base_header(self, key, value):
        """
        Base headers will be sent by default with any request
        These may be overridden by additional headers given as kwargs parameter
        Existing keys will be overwritten
        """
        self.base_headers[key] = value

    def pop_base_header(self, key):
        """
        Remove base header
        """
        return self.base_headers.pop(key)

    def request(self, *args: Any, **kwargs: Any) -> Any:
        method = args[0] if len(args) >= 1 else kwargs.get("method")
        url = args[1] if len(args) >= 2 else kwargs.get("url")
        request_headers = kwargs.get("headers", {})
        consolidated_headers = {**self.base_headers, **request_headers}
        try:
            r = super().request(
                *args, **{
                    **kwargs,
                    "auth": self.credentials,
                    "headers": consolidated_headers,
                    "verify": self.verifytls,
                }
            )
        except (ConnectTimeout, ConnectionError) as err:
            logger.debug("[%s] %s: %s", method, url, err.__class__.__name__)
            raise TimeoutException({"message": f"connection failed to {url}", "error": err})
        logger.debug("[%s] %s, status %s", method, url, r.status_code)
        logger.debug("Headers: %s", consolidated_headers)
        if r.status_code in [401, 403]:
            logger.debug("Authentication failed at [%s] %s", method, url)
            raise AuthException(r.status_code, {"message": f"auth failed at {url}", "response": r})
        return r
