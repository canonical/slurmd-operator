# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

from pytest import fixture
from pytest_operator.plugin import OpsTest


@fixture(scope="module")
async def slurmd_charm(ops_test: OpsTest):
    charm = await ops_test.build_charm(".")
    return charm
