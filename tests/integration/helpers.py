# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import urllib.request

from pathlib import Path

NHC_URL = "https://github.com/mej/nhc/releases/download/1.4.3/lbnl-nhc-1.4.3.tar.gz"
NHC_PATH = "lbnl-nhc-1.4.3.tar.gz"
VERSION = "v1.0.0"
VERSION_PATH = "version"


def fetch_deps() -> dict:
    nhc = Path(NHC_PATH)
    version = Path(VERSION_PATH)
    if nhc.exists():
        pass
    else:
        # fetch NHC resource
        urllib.request.urlretrieve(NHC_URL, NHC_PATH)
    if version.exists():
        pass
    else:
        # create version file
        with open(VERSION_PATH, "w") as f:
            f.write(VERSION)
    return {"nhc": nhc}
