import pytest
from geonetwork.exceptions import GnException, APIVersionException, CustomExceptionConfig, GnExceptionHandler


class CustomException(Exception):
    def __init__(self, code, stack):
        self.code = code
        self.stack = stack
        super().__init__()


def map_fn(code, details, **kwargs):
    return ([code, details], {"code": code, "stack": [details]})


custom_conf = CustomExceptionConfig(CustomException, map_fn)
exc_hdl = GnExceptionHandler(custom_conf)


def test_basic_exception():
    exc_hdl = GnExceptionHandler()
    built_exception = exc_hdl.build_exception()
    with pytest.raises(built_exception) as err:
        raise built_exception(404, ["stack1", "stack2"])
    assert isinstance(err.value, Exception)
    assert isinstance(err.value, GnException)


def test_api_version_exception():
    exc_hdl = GnExceptionHandler()
    built_exception = exc_hdl.build_exception(APIVersionException)
    with pytest.raises(built_exception) as err:
        raise built_exception(404, ["stack1", "stack2"])
    assert isinstance(err.value, Exception)
    assert isinstance(err.value, GnException)
    assert isinstance(err.value, APIVersionException)


def test_built_in_exception():
    exc_hdl = GnExceptionHandler(CustomExceptionConfig(NotImplementedError))
    built_exception = exc_hdl.build_exception()
    with pytest.raises(built_exception) as err:
        raise built_exception(404, ["stack1", "stack2"])
    assert isinstance(err.value, NotImplementedError)


def test_exception_attrib():
    exc_hdl = GnExceptionHandler(CustomExceptionConfig(NotImplementedError))
    built_exception = exc_hdl.APIVersionException
    with pytest.raises(APIVersionException) as err:
        raise built_exception(404, ["stack1", "stack2"])
    assert isinstance(err.value, NotImplementedError)


def test_exception_attrib_missing_key():
    exc_hdl = GnExceptionHandler(CustomExceptionConfig(NotImplementedError))
    with pytest.raises(NameError) as err:
        exc_hdl.InexistenException
    assert "is not defined" in str(err.value)


def test_custom_exception():
    exc_hdl = GnExceptionHandler(CustomExceptionConfig(CustomException))
    built_exception = exc_hdl.build_exception()
    with pytest.raises(built_exception) as err:
        raise built_exception(404, ["stack1", "stack2"])
    assert not isinstance(err.value, NotImplementedError)
    assert isinstance(err.value, CustomException)
    assert err.value.stack == ["stack1", "stack2"]


def test_custom_exception_map():
    exc_hdl = GnExceptionHandler(custom_conf)
    built_exception = exc_hdl.build_exception()
    with pytest.raises(built_exception) as err:
        raise built_exception(404, "detailed err")
    assert not isinstance(err.value, NotImplementedError)
    assert isinstance(err.value, CustomException)
    assert err.value.stack == ["detailed err"]


def test_custom_exception_map_kwargs():
    exc_hdl = GnExceptionHandler(custom_conf)
    built_exception = exc_hdl.build_exception()
    with pytest.raises(built_exception) as err:
        raise built_exception(details="detailed err", code=404)
    assert not isinstance(err.value, NotImplementedError)
    assert isinstance(err.value, CustomException)
    assert err.value.stack == ["detailed err"]


def test_custom_exception_invalid_class():
    class OtherClass:
        pass
    with pytest.raises(TypeError) as err:
        CustomExceptionConfig(OtherClass)
    assert "is not a subclass of Exception" in str(err.value.args)


def test_custom_exception_invalid_functions():
    with pytest.raises(TypeError) as err:
        CustomExceptionConfig(CustomException, 5)
    assert "is not callable" in str(err.value.args)
