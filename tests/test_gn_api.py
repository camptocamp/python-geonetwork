import pytest
from requests.exceptions import HTTPError
import requests_mock
from geonetwork import GnApi


@pytest.fixture
def init_gn():
    with requests_mock.Mocker() as m:
        cookies = requests_mock.CookieJar()
        cookies.set("XSRF-TOKEN", "dummy_xsrf", path="/geonetwork")

        def site_callback(request, context):
            print(request.headers)
            assert request.headers.get("accept") == "application/json"
            return {"system/platform/version": "4.3.2"}
        m.get('http://geonetwork/api/site', json=site_callback, cookies=cookies)
        gn = GnApi("http://geonetwork/api")
        return gn


def test_init(init_gn):
    assert init_gn.xsrf_token == "dummy_xsrf"


def test_failed_credentials():
    with requests_mock.Mocker() as m:
        cookies = requests_mock.CookieJar()
        cookies.set("XSRF-TOKEN", "dummy_xsrf", path="/geonetwork")

        def site_callback(request, context):
            context.status_code = 401
            return {"system/platform/version": "4.3.2"}
        m.get('http://geonetwork/api/site', json=site_callback, cookies=cookies)
        with pytest.raises(HTTPError) as err:
            GnApi("http://geonetwork/api")
        assert "401" in str(err.value)


def test_record_zip(init_gn):
    with requests_mock.Mocker() as m:

        def record_callback(request, context):
            print(request.headers)
            assert request.headers.get("accept") == "application/zip"
            return b"dummy_zip"
        m.get('http://geonetwork/api/records/1234', content=record_callback)
        zipdata = init_gn.get_record_zip("1234")
        assert zipdata == b"dummy_zip"
