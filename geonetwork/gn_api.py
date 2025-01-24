from io import BytesIO
from typing import Union, Literal, Any
from .gn_session import GnSession, Credentials, logger
from .exceptions import APIVersionException, ParameterException


GN_VERSION_RANGE = ["4.2.8", "4.4.5"]


class GnApi:
    def __init__(
        self,
        api_url: str,
        credentials: Union[Credentials, None] = None,
        verifytls: bool = True,
    ):
        self.api_url = api_url
        self.credentials = credentials

        self.session = GnSession(self.credentials, verifytls)
        self.session.set_base_header("Accept", "application/json")
        self.init_xsrf_token()

    def init_xsrf_token(self):
        resp = self.get_version()
        self.xsrf_token = resp.cookies.get("XSRF-TOKEN", path="/geonetwork")
        self.session.set_base_header("X-XSRF-TOKEN", self.xsrf_token)

    def get_version(self):
        version_url = self.api_url + "/site"
        resp = self.session.get(version_url)
        resp.raise_for_status()
        version = resp.json().get("system/platform/version")
        if (
            (version is None)
            or (version < GN_VERSION_RANGE[0])
            or (version > GN_VERSION_RANGE[1])
        ):
            raise APIVersionException(
                {
                    "code": 501,
                    "msg": f"Version {version} not in allowed range {GN_VERSION_RANGE}",
                }
            )
        logger.info("GN API Session started with geonetwork server version %s", version)
        return resp

    def get_record_zip(self, uuid: str) -> bytes:
        resp = self.session.get(
            f"{self.api_url}/records/{uuid}",
            headers={"accept": "application/zip"},
        )
        if resp.status_code == 404:
            raise ParameterException({"code": 404, "msg": f"UUID {uuid} not found"})
        resp.raise_for_status()
        return resp.content

    def put_record_zip(self, zipdata: bytes, overwrite: bool = True) -> Any:
        resp = self.session.post(
            f"{self.api_url}/records",
            files={"file": ("file.zip", BytesIO(zipdata), "application/zip")},
            params={
                "metadataType": "METADATA",
                "uuidProcessing": "OVERWRITE" if overwrite else "GENERATEUUID",
            },
        )
        resp.raise_for_status()
        return resp.json()

    def get_metadataxml(self, uuid):
        headers = {
            'Accept': 'application/xml',
        }
        url = self.server + "/records/"+uuid
        resp = self.session.get(
            url,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.content

    UuidProcs = Literal["NOTHING", "OVERWRITE", "GENERATEUUID", "REMOVE_AND_REPLACE"]

    def upload_metadata(self, metadata, groupid='100', uuidprocessing: UuidProcs = "GENERATEUUID", publish=False):

        # Set the parameters
        params = {
            'metadataType': 'METADATA',
            'uuidProcessing': uuidprocessing,
            'transformWith': '_none_',
            'group': groupid,
            'publishToAll': str(publish).lower()
        }

        response = self.session.post(
            self.api_url + '/records',
            json=params,
            params=params,
            files={"file": metadata},
        )
        response.raise_for_status()
        return response

    def get_thesaurus_dict(self):
        url = self.api_url.replace("/api", "") + "/fre/thesaurus?_content_type=json"
        response = self.session.get(url)
        return response.json()

    def add_thesaurus_dict(self, filename):
        """
        Not working yet
        ongoing
        """
        headers = {
            'Accept': 'application/json',
            'X-XSRF-TOKEN': self.xsrf_token,
            'Origin': 'http://'+self.server,
            'Referer': 'http://'+self.server+'/geonetwork/srv/fre/admin.console',
        }

        # Set the parameters
        params = {
            '_csrf': self.xsrf_token,
            'url': '',
            'registryUrl': '',
            'registryType': '',
            'type': 'local',
            'dir': 'theme',
        }  # 'stylesheet': '_none_',

        cookies = {
            'XSRF-TOKEN': self.xsrf_token,
        }
        response = self.session.post(
            self.server + '/geonetwork/srv/api/registries/vocabularies?_csrf='+self.xsrf_token,
            auth=(self.username, self.password),
            headers=headers, cookies=cookies, data=params, verify=self.verifytls,
            files=[('file', (filename, open(filename, 'rb').read(), 'application/rdf+xml'))]
        )
        self.session.close()
        req = response.request
        print('{}\n{}\r\n{}\r\n\r\n{}'.format(
            '-----------START-----------',
            req.method + ' ' + req.url,
            '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            req.body,
        ))
        print(response.request)
        print("uploaded new thesaurus")
        print(response)
        print(response.text)

    def delete_thesaurus_dict(self, name):
        """
        Use geonetwork API to remove a thesaurus entry
        :param name: The name of the refered entry should look like
                     [internal|external].[theme|place|...].[name]
        """
        url = self.api_url + "/registries/vocabularies/" + name
        response = self.session.delete(url)
        response.raise_for_status()
        return response.json()

    def close_session(self):
        self.session.close()
