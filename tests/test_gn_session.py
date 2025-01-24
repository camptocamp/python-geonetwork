from geonetwork import GnSession
import requests_mock


def test_anonymous():
    gns = GnSession()
    with requests_mock.Mocker() as m:

        def text_callback(request, context):
            assert "Authorization" not in request.headers
            return "bla"
        m.get("http://bla", text=text_callback)
        resp = gns.get("http://bla")
        assert resp.text == "bla"


def test_post():
    gns = GnSession()
    with requests_mock.Mocker() as m:
        m.post("http://bla", text="post")
        resp = gns.post("http://bla")
        assert resp.text == "post"


def test_headers():
    gns = GnSession()
    with requests_mock.Mocker() as m:

        def header_callback(request, context):
            return dict(request.headers)
        m.get("http://bla", json=header_callback)
        resp = gns.get("http://bla")
        assert resp.json().get("test-header") is None
        gns.set_base_header("Test-Header", "test")
        gns.set_base_header("referer", "http://me")
        resp = gns.get("http://bla")
        assert resp.json().get("Test-Header") == "test"
        assert resp.json().get("referer") == "http://me"
        resp = gns.get("http://bla")
        assert gns.pop_base_header("referer") == "http://me"
        resp = gns.get("http://bla")
        assert resp.json().get("referer") is None


def test_auth():
    gns = GnSession(("test", "test"))
    with requests_mock.Mocker() as m:

        def text_callback(request, context):
            assert "Authorization" in request.headers
            return "bla"
        m.get("http://bla", text=text_callback)
        resp = gns.get("http://bla")
        assert resp.text == "bla"


def test_invalid_credentials():
    gns = GnSession(("test", "test"))
    with requests_mock.Mocker() as m:

        def text_callback(request, context):
            context.status_code = 401
            return "bla"
        m.get("http://bla", text=text_callback)
        resp = gns.get("http://bla")
        assert resp.status_code == 401
