# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import urllib.request
import yaml

from pathlib import Path

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
ETCD_URL = "https://github.com/etcd-io/etcd/releases/download/v3.5.0/etcd-v3.5.0-linux-amd64.tar.gz"
ETCD_PATH = "etcd-v3.5.0-linux-amd64.tar.gz"
NHC_URL = "https://github.com/mej/nhc/releases/download/1.4.3/lbnl-nhc-1.4.3.tar.gz"
NHC_PATH = METADATA["resources"]["nhc"]["filename"]
VERSION = "0.8.5"
VERSION_PATH = "version"


def fetch_slurmd_deps() -> dict:
    """Slurmd depends on NHC tarball and version file."""
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

def fetch_slurmctld_deps() -> dict:
    """Slurmctld depends on etcd """
    etcd = Path(ETCD_PATH)
    if etcd.exists():
        pass
    else:
        # fetch ETCD resource
        urllib.request.urlretrieve(ETCD_URL, ETCD_PATH)
    return {"etcd": etcd}
