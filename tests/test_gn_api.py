import pytest
from io import BytesIO
from requests.exceptions import HTTPError
import requests_mock
from geonetwork import GnApi
from geonetwork.exceptions import APIVersionException, ParameterException


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


def test_unsupported_version():
    with requests_mock.Mocker() as m:
        cookies = requests_mock.CookieJar()
        cookies.set("XSRF-TOKEN", "dummy_xsrf", path="/geonetwork")

        def site_callback(request, context):
            return {"system/platform/version": "0.1.1"}
        m.get('http://geonetwork/api/site', json=site_callback, cookies=cookies)
        with pytest.raises(APIVersionException) as err:
            GnApi("http://geonetwork/api")
        assert err.value.args[0]["code"] == 501


def test_record_zip(init_gn):
    with requests_mock.Mocker() as m:

        def record_callback(request, context):
            print(request.headers)
            assert request.headers.get("accept") == "application/zip"
            return b"dummy_zip"
        m.get('http://geonetwork/api/records/1234', content=record_callback)
        zipdata = init_gn.get_record_zip("1234")
        assert zipdata.read() == b"dummy_zip"


def test_record_zip_unknown_uuid(init_gn):
    with requests_mock.Mocker() as m:
        m.get('http://geonetwork/api/records/1234', content=b"ok")
        m.get('http://geonetwork/api/records/1232', status_code=404)
        with pytest.raises(ParameterException) as err:
            init_gn.get_record_zip("1232")
        assert err.value.args[0]["code"] == 404


def test_upload_zip(init_gn):
    with requests_mock.Mocker() as m:

        def creation_callback(request, context):
            assert request.headers.get("accept") == "application/json"
            assert request.headers.get('Content-Length') == '184'
            assert request.headers.get('X-XSRF-TOKEN') == "dummy_xsrf"
            assert 'multipart/form-data' in request.headers.get("Content-Type")
            assert "application/zip" in request.text
            assert "dummy_zip" in request.text
            return {"errors": [], "metadataInfos": {101: {}}}
        m.post('http://geonetwork/api/records', json=creation_callback)

        def record_callback(request, context):
            assert request.headers.get("accept") == "application/json"
            assert request.headers.get('X-XSRF-TOKEN') == "dummy_xsrf"
            return {
                "gmd:fileIdentifier": {
                    "gco:CharacterString": {
                        "#text": "pseuso_uuid-1234-55ac"
                    }
                }
            }
        m.get('http://geonetwork/api/records/101', json=record_callback)
        zipdata = BytesIO(b"dummy_zip")
        resp = init_gn.put_record_zip(zipdata)
        assert resp["msg"] == "Metadata creation successful (pseuso_uuid-1234-55ac)"


def test_upload_zip_fail(init_gn):
    with requests_mock.Mocker() as m:

        def record_callback(request, context):
            assert request.headers.get("accept") == "application/json"
            assert request.headers.get('Content-Length') == '184'
            assert request.headers.get('X-XSRF-TOKEN') == "dummy_xsrf"
            assert 'multipart/form-data' in request.headers.get("Content-Type")
            assert "application/zip" in request.text
            assert "dummy_zip" in request.text
            return {
                "errors": [
                    {"message": "err1", "stack": "line1\nline2"},
                    {"message": "err2", "stack": "e2/line1\n\tat e2/line2"},
                ]
            }
        m.post('http://geonetwork/api/records', json=record_callback)
        zipdata = BytesIO(b"dummy_zip")
        with pytest.raises(ParameterException) as err:
            init_gn.put_record_zip(zipdata)
        assert err.value.args[0]["code"] == 404
        assert err.value.args[0]["details"] == [
            {"message": "err1", "stack": ["line1", "line2"]},
            {"message": "err2", "stack": ["e2/line1", "    at e2/line2"]},
        ]
