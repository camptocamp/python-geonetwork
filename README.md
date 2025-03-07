# python-geonetwork
python bindings to geonetwork API

This library simplifies the API call to a geonetwork instance for use in python apps

## Installation

From PyPI:

TODO: not yet deployed on PyPi


From git repository:

```
git clone https://github.com/camptocamp/python-geonetwork
cd python-geonetwork
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## Basic use

Currently only the interface for zip and xml metadata records is implemented.

Example 1: Get zip data

```
from geonetwork import GnApi
gn_api = GnApi("https://demo.georchestra.org/geonetwork/srv/api")
zipdata = gn_api.get_record_zip("c8166e8f-36a2-40ca-af1a-a00ab1fb20f7")
import zipfile
with zipfile.ZipFile(zipdata) as zf:
    for f in zf.filelist:
        print(f)
with zipfile.ZipFile(zipdata) as zf:
    with zf.open("c8166e8f-36a2-40ca-af1a-a00ab1fb20f7/info.xml") as f:
        print(f.read().decode())
```

Example 2: upload zip data

```
with open("./meta.zip") as f:
    GnApi("http://localhost:9090/geonetwork/srv/api", ("admin", "admin")).put_record_zip(f)
```

## Detailed description of library

### class GnApi

#### Constructor:

```
GnApi(api_url, credentials, verifytls)
```

- api_url: direct url to the geonetwork API, usually ends with `/geonetwork/srv/api`
- credentials: tuple of (login, password)
- verifytls: boolean, default True. can be set to False in case of https servers with invalid certificates (e.g. in a local dev instance)

The constructor performs a handshake operation with the geonetwork server:
- check geonetwork version
- get XSRF-token
- store XSRF token in headers for the current session. all API calls within this instance of GnApi use this XSRF token

The returned GnApi instance is ready for operation

#### Methods

- `get_record_zip(uuid)` : retrieve the metadata for `uuid` as a zip archive including linked media. The metadata is returned as a bytes object
- `put_record_zip(zipdata, overwrite)` : upload a zip archive given as bytes object. Overwrite existing data or create a new record


## Command line scripts

TODO
