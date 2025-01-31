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


class CustomExceptionConfig(BaseExceptionConfig):
    def __init__(self, base_exception, map_function=None):
        if not issubclass(base_exception, Exception):
            raise TypeError(f"{base_exception} is not a subclass of Exception")
        self.base_exception = base_exception
        if map_function is not None:
            if not callable(map_function):
                raise TypeError(f"{map_function} is not callable")
        self.map_function = map_function

    def map_gn_to_base_function(self, *args, **kwargs):
        if self.map_function is None:
            if len(args) >= 1:
                code = args[0]
            else:
                code = kwargs["code"]
            if len(args) >= 2:
                details = args[1]
            else:
                details = kwargs["code"]
            return ([code, details, code, details], {})
        return self.map_function(*args, **kwargs)


class GnExceptionHandler:
    def __init__(self, exception_config=None):
        if exception_config is None:
            exception_config = BaseExceptionConfig()
        self.base_exception = exception_config.base_exception
        self.map_function = exception_config.map_gn_to_base_function

    def __getattr__(self, key):
        # !!! security concerns ?
        if issubclass(eval(key), GnException):
            return self.build_exception(eval(key))
        raise KeyError(f'GnException "{key}" does not exist')

    def build_exception(self, gn_exception=GnException):
        class BuiltException(gn_exception, self.base_exception):
            def __init__(inner_self, *args, **kwargs):
                super_args, super_kwargs = self.map_function(*args, **kwargs)
                super().__init__(*super_args, **super_kwargs)
        return BuiltException
