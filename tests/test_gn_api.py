import pytest
from zipfile import ZipFile
from io import BytesIO
from requests.exceptions import HTTPError
import requests_mock
from geonetwork import GnApi
from geonetwork.exceptions import APIVersionException, ParameterException, AuthException, GnException, GnElasticException


@pytest.fixture
def init_gn():
    with requests_mock.Mocker() as m:
        cookies = requests_mock.CookieJar()
        cookies.set("XSRF-TOKEN", "dummy_xsrf", path="/geonetwork")

        def site_callback(request, context):
            assert request.headers.get("accept") == "application/json"
            return {"system/platform/version": "4.3.2"}
        m.get('http://geonetwork/api/site', json=site_callback, cookies=cookies)
        gn = GnApi("http://geonetwork/api")
        return gn


@pytest.fixture
def zipdata():
    zz = BytesIO()
    with ZipFile(zz, "w") as zf:
        with zf.open("index.csv", "w") as ii:
            ii.write(b'"schema";"uuid";"id";"type";"isHarvested";"title";"abstract"\n"iso19139";"859ebc17-6811-48f6-a7ef-b9a29ad94f95";"39636";"METADATA";"true";"-";"-"\n')
        with zf.open("859ebc17-6811-48f6-a7ef-b9a29ad94f95/metadata/metadata.xml", "w") as xx:  
            xx.write(b"<dummy><xml></xml></dummy>")
    return zz


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
        with pytest.raises(AuthException) as err:
            GnApi("http://geonetwork/api")
        assert err.value.code == 401


def test_unsupported_version():
    with requests_mock.Mocker() as m:
        cookies = requests_mock.CookieJar()
        cookies.set("XSRF-TOKEN", "dummy_xsrf", path="/geonetwork")

        def site_callback(request, context):
            return {"system/platform/version": "0.1.1"}
        m.get('http://geonetwork/api/site', json=site_callback, cookies=cookies)
        with pytest.raises(APIVersionException) as err:
            GnApi("http://geonetwork/api")
        assert err.value.code == 501


def test_record_zip(init_gn):
    with requests_mock.Mocker() as m:

        def record_callback(request, context):
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
        assert err.value.code == 400


def test_upload_zip(init_gn, zipdata):
    with requests_mock.Mocker() as m:

        def creation_callback(request, context):
            assert request.headers.get("accept") == "application/json"
            assert request.headers.get('Content-Length') == '175'
            assert request.headers.get('X-XSRF-TOKEN') == "dummy_xsrf"
            assert 'multipart/form-data' in request.headers.get("Content-Type")
            assert "application/zip" in request.text
            assert "filename=\"file.zip\"\r\nContent-Type: application/zip" in request.text
            return {"errors": [], "metadataInfos": {101: [{"uuid": 101}]}}
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
        # zipdata = BytesIO(b"dummy_zip")
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
        assert err.value.code == 400
        assert err.value.detail.info["stack"] == [
            {"message": "err1", "stack": ["line1", "line2"]},
            {"message": "err2", "stack": ["e2/line1", "    at e2/line2"]},
        ]


def test_search(init_gn):
    QUERY_TEXT = (
        '{"query": {"bool": {"must": [{"terms": {"isTemplate": ["n"]}}, '
        '{"multi_match": {"query": "test", "type": "bool_prefix", "fields": '
        '["resourceTitleObject.*^4", "resourceAbstractObject.*^3", "tag^2", '
        '"resourceIdentifier"]}}], "must_not": {"terms": {"resourceType": '
        '["service", "map", "map/static", "mapDigital"]}}}}, "_source": '
        '["resourceTitleObject", "uuid"], "from": 0, "size": 20}'
    )
    QUERY_JSON = {
        "query": {
            "bool": {
                "must": [
                    {
                        "terms": {
                            "isTemplate": [
                                "n"
                            ]
                        }
                    },
                    {
                        "multi_match": {
                            "query": "test",
                            "type": "bool_prefix",
                            "fields": [
                                "resourceTitleObject.*^4",
                                "resourceAbstractObject.*^3",
                                "tag^2",
                                "resourceIdentifier"
                            ]
                        }
                    }
                ],
                "must_not": {
                    "terms": {
                        "resourceType": [
                            "service",
                            "map",
                            "map/static",
                            "mapDigital"
                        ]
                    }
                }
            }
        },
        "_source": [
            "resourceTitleObject",
            "uuid"
        ],
        "from": 0,
        "size": 20
    }

    with requests_mock.Mocker() as m:
        def search_callback(request, context):
            assert request.headers.get("accept") == "application/json"
            assert request.text == QUERY_TEXT
            assert request.headers.get('X-XSRF-TOKEN') == "dummy_xsrf"
            return {"created": "success"}
        m.post('http://geonetwork/api/search/records/_search', json=search_callback)
        init_gn.search(QUERY_JSON)


def test_search_fail(init_gn):
    with requests_mock.Mocker() as m:
        def search_callback(request, context):
            context.status_code = 400
            return {
                "servlet": "spring",
                "message": (
                    "Error is: Bad Request.\nRequest:\n{&quot;query&quot;:"
                    "{&quot;bool&quot;:{&quot;must&quot;:{},&quot;filter&quot;:"
                    "{&quot;query_string&quot;:{&quot;query&quot;:&quot;*:* AND "
                    "(draft:n OR draft:e)&quot;}}}}}\n.\nError:\n{&quot;error&quot;:"
                    "{&quot;root_cause&quot;:[{&quot;type&quot;:&quot;x_content_"
                    "parse_exception&quot;,&quot;reason&quot;:&quot;[1:27] [bool] "
                    "failed to parse field [must]&quot;}],&quot;type&quot;:&quot;"
                    "x_content_parse_exception&quot;,&quot;reason&quot;:&quot;[1:27] "
                    "[bool] failed to parse field [must]&quot;,&quot;caused_by&quot;:"
                    "{&quot;type&quot;:&quot;illegal_argument_exception&quot;,&quot;"
                    "reason&quot;:&quot;query malformed, empty clause found at [1:27]"
                    "&quot;}},&quot;status&quot;:400}."
                )
            }
        m.post('http://geonetwork/api/search/records/_search', json=search_callback)
        with pytest.raises(GnElasticException) as err:
            init_gn.search({"query": {}})
        assert err.value.code == 400
        assert list(err.value.detail.info.keys()) == ["info_0", "Request:", "Error:"]
