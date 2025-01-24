class GnException(Exception):
    pass


class AuthException(GnException):
    pass


class APIVersionException(GnException):
    pass


class ParameterException(GnException):
    pass
