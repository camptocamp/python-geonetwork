from logging import Handler
import requests_mock
from geonetwork import GnApi
from geonetwork.gn_logger import logger


def test_log_object():
    class LogHandler(Handler):
        responses = []

        def emit(self, record):
            try:
                self.responses.append(record.response)
            except AttributeError:
                self.responses.append(None)

    log_handler = LogHandler()
    logger.addHandler(log_handler)
    with requests_mock.Mocker() as m:
        cookies = requests_mock.CookieJar()
        cookies.set("XSRF-TOKEN", "dummy_xsrf", path="/geonetwork")

        def site_callback(request, context):
            assert request.headers.get("accept") == "application/json"
            return {"system/platform/version": "4.3.2"}
        m.get('http://geonetwork/api/site', json=site_callback, cookies=cookies)
        gn = GnApi("http://geonetwork/api")

        def record_callback(request, context):
            print(request.headers)
            assert request.headers.get("accept") == "application/zip"
            return b"dummy_zip"
        m.get('http://geonetwork/api/records/1234', content=record_callback)
        zipdata = gn.get_record_zip("1234")
        assert zipdata.read() == b"dummy_zip"
        URLs = [r.url for r in log_handler.responses if r is not None]
        assert URLs == ['http://geonetwork/api/site', 'http://geonetwork/api/records/1234']
