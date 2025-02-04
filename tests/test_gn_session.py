import requests_mock
from requests.exceptions import ConnectTimeout
import pytest
from geonetwork import GnSession
from geonetwork.exceptions import AuthException, GnRequestException


def test_anonymous():
    gns = GnSession()
    with requests_mock.Mocker() as m:

        def text_callback(request, context):
            assert "Authorization" not in request.headers
            return "test"
        m.get("http://mock_server", text=text_callback)
        resp = gns.get("http://mock_server")
        assert resp.text == "test"


def test_post():
    gns = GnSession()
    with requests_mock.Mocker() as m:
        m.post("http://mock_server", text="post")
        resp = gns.post("http://mock_server")
        assert resp.text == "post"


def test_headers():
    gns = GnSession()
    with requests_mock.Mocker() as m:

        def header_callback(request, context):
            return dict(request.headers)
        m.get("http://mock_server", json=header_callback)
        resp = gns.get("http://mock_server")
        assert resp.json().get("test-header") is None
        gns.set_base_header("Test-Header", "test")
        gns.set_base_header("referer", "http://me")
        resp = gns.get("http://mock_server")
        assert resp.json().get("Test-Header") == "test"
        assert resp.json().get("referer") == "http://me"
        resp = gns.get("http://mock_server")
        assert gns.pop_base_header("referer") == "http://me"
        resp = gns.get("http://mock_server")
        assert resp.json().get("referer") is None


def test_auth():
    gns = GnSession(("test", "test"))
    with requests_mock.Mocker() as m:

        def text_callback(request, context):
            assert "Authorization" in request.headers
            return "test"
        m.get("http://mock_server", text=text_callback)
        resp = gns.get("http://mock_server")
        assert resp.text == "test"


def test_invalid_credentials():
    gns = GnSession(("test", "test"))
    with requests_mock.Mocker() as m:

        def text_callback(request, context):
            context.status_code = 401
            return "test"
        m.get("http://mock_server", text=text_callback)
        with pytest.raises(AuthException) as err:
            gns.get("http://mock_server")
        assert err.value.code == 401


def test_timeout():
    gns = GnSession(("test", "test"))
    with requests_mock.Mocker() as m:

        def timeout_callback(request, context):
            raise ConnectTimeout
        m.get("http://mock_server", text=timeout_callback)
        with pytest.raises(GnRequestException) as err:
            gns.get("http://mock_server")
        assert err.value.code == 504
