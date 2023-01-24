# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Configure integration test run."""

import pathlib

from pytest import fixture
from pytest_operator.plugin import OpsTest

from helpers import ETCD, NHC, VERSION


@fixture(scope="module")
async def slurmd_charm(ops_test: OpsTest):
    charm = await ops_test.build_charm(".")
    return charm

def pytest_sessionfinish(session, exitstatus) -> None:
    """Clean up repository after test session has completed."""
    pathlib.Path(ETCD).unlink(missing_ok=True)
    pathlib.Path(NHC).unlink(missing_ok=True)
    pathlib.Path(VERSION).unlink(missing_ok=True)
