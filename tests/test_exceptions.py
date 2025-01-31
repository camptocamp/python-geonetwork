import pytest
from geonetwork.exceptions import GnException, APIVersionException, build_exception


class CustomException(Exception):
    def __init__(self, code, stack):
        self.code = code
        self.stack = stack
        super().__init__()


def test_basic_exception():
    built_exception = build_exception(Exception)
    with pytest.raises(built_exception) as err:
        raise built_exception(404, ["stack1", "stack2"])
    assert isinstance(err.value, Exception)
    assert isinstance(err.value, GnException)


def test_api_version_exception():
    built_exception = build_exception(Exception, APIVersionException)
    with pytest.raises(built_exception) as err:
        raise built_exception(404, ["stack1", "stack2"])
    assert isinstance(err.value, Exception)
    assert isinstance(err.value, GnException)
    assert isinstance(err.value, APIVersionException)


def test_built_in_exception():
    built_exception = build_exception(NotImplementedError)
    with pytest.raises(built_exception) as err:
        raise built_exception(404, ["stack1", "stack2"])
    assert isinstance(err.value, NotImplementedError)


def test_custom_exception():
    built_exception = build_exception(CustomException)
    with pytest.raises(built_exception) as err:
        raise built_exception(404, ["stack1", "stack2"])
    assert not isinstance(err.value, NotImplementedError)
    assert isinstance(err.value, CustomException)
    assert err.value.stack == ["stack1", "stack2"]


def test_custom_exception_map():

    def map_fn(code, details, **kwargs):
        return ([code, details], {"code": code, "stack": [details]})
    built_exception = build_exception(CustomException, map_function=map_fn)
    with pytest.raises(built_exception) as err:
        raise built_exception(404, "detailed err")
    assert not isinstance(err.value, NotImplementedError)
    assert isinstance(err.value, CustomException)
    assert err.value.stack == ["detailed err"]
