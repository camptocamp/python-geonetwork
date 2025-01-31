class GnException(Exception):
    def __init__(self, gn_code, gn_details, *args, **kwargs):
        self.code = gn_code
        self.details = gn_details
        super().__init__(*args, **kwargs)


class AuthException(GnException):
    pass


class APIVersionException(GnException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ParameterException(GnException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class BaseExceptionConfig:
    base_exception = Exception

    def map_gn_to_base_function(self, code, details):
        return ([code, details, code, details], {})


def identity(*args, **kwargs):
    return ([200, "OK", *args], kwargs)


def build_exception(base_exception, gn_exception=GnException, map_function=None):
    if map_function is None:
        map_function = identity
    elif not callable(map_function):
        raise TypeError('Given parameter "map_gn_to_base_function" must be callable')

    class BuiltException(gn_exception, base_exception):
        def __init__(self, *args, **kwargs):
            super_args, super_kwargs = map_function(*args, **kwargs)
            super().__init__(*super_args, **super_kwargs)
    return BuiltException
