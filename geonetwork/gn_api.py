from io import BytesIO
from typing import Union, Literal, IO, Any
from .gn_session import GnSession, Credentials, logger
from .exceptions import APIVersionException, ParameterException, BaseExceptionConfig, build_exception


GN_VERSION_RANGE = ["4.2.8", "4.4.5"]


class GnApi:
    def __init__(
        self,
        api_url: str,
        credentials: Union[Credentials, None] = None,
        verifytls: bool = True,
        base_exception_config=None,
    ):
        """
        Initialize the GnApi object

        The following handshake operation is perfomed with the geonetwork server:
        - check geonetwork version
        - get XSRF-token
        - store XSRF token in headers for the current session. all API calls within this instance of GnApi use this XSRF token

        :param api_url: direct url to the geonetwork API, usually ends with `/geonetwork/srv/api`
        :param credentials: tuple of (login, password)
        :param verifytls: boolean, default True. can be set to False in case of https servers with invalid certificates (e.g. in a local dev instance)
        """
        if base_exception_config is None:
            base_exception_config = BaseExceptionConfig()
        base_exception = base_exception_config.base_exception
        conversion_fn = base_exception_config.map_gn_to_base_function
        self.api_version_exception = build_exception(base_exception, APIVersionException, conversion_fn)
        self.parameter_exception = build_exception(base_exception, ParameterException, conversion_fn)
        self.api_url = api_url
        self.credentials = credentials

        self.session = GnSession(self.credentials, verifytls)
        self.session.set_base_header("Accept", "application/json")
        self._init_xsrf_token()

    def _init_xsrf_token(self):
        resp = self._get_version()
        self.xsrf_token = resp.cookies.get("XSRF-TOKEN", path="/geonetwork")
        self.session.set_base_header("X-XSRF-TOKEN", self.xsrf_token)

    def _get_version(self):
        version_url = self.api_url + "/site"
        resp = self.session.get(version_url)
        resp.raise_for_status()
        version = resp.json().get("system/platform/version")
        if (
            (version is None)
            or (version < GN_VERSION_RANGE[0])
            or (version > GN_VERSION_RANGE[1])
        ):
            raise self.api_version_exception(
                code=501,
                details=f"Version {version} not in allowed range {GN_VERSION_RANGE}",
            )
        logger.info("GN API Session started with geonetwork server version %s", version)
        return resp

    def get_record_zip(self, uuid: str) -> IO[bytes]:
        """
         retrieve the metadata for `uuid` as a zip archive including linked media.
        :param uuid: uuid of the metadata
        :returns: BytesIO file-type output data - the metadata is returned as a bytes object
        """
        resp = self.session.get(
            f"{self.api_url}/records/{uuid}",
            headers={"accept": "application/zip"},
        )
        if resp.status_code == 404:
            raise self.parameter_exception(code=404, details=f"UUID {uuid} not found")
        resp.raise_for_status()
        return BytesIO(resp.content)

    def put_record_zip(self, zipdata: IO[bytes], overwrite: bool = True) -> Any:
        """
         upload metadata as a zip archive.
        :param zipdata: file-like object of the zip file (may also be BytesIO(constant_bytes))
        :param overwrite: boolean [True] overwrite existing data or create a new record with new uuid
        :returns: dict of the response including success of the operation, uuid, etc.
        """
        resp = self.session.post(
            f"{self.api_url}/records",
            files={"file": ("file.zip", zipdata, "application/zip")},
            params={
                "metadataType": "METADATA",
                "uuidProcessing": "OVERWRITE" if overwrite else "GENERATEUUID",
            },
        )
        resp.raise_for_status()
        results = resp.json()
        if results["errors"]:
            clean_error_stack = [
                {
                    **err,
                    "stack": [t.replace("\t", "    ") for t in err.get("stack", []).split("\n")]
                }
                for err in results["errors"]
            ]

            raise self.parameter_exception(code=404, details=clean_error_stack)

        # take first id of results ids
        serial_id = next(iter(results["metadataInfos"].values()))["uuid"]
        metadata_json = self.session.get(
            f"{self.api_url}/records/{serial_id}",
            headers={"accept": "application/json"},
        ).json()
        uuid = metadata_json["gmd:fileIdentifier"]["gco:CharacterString"]["#text"]
        return {
            "msg": f"Metadata creation successful ({uuid})",
            "detail": results,
        }

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
