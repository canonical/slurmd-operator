#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import pytest 
import requests

from helpers import fetch_deps

from pytest_operator.plugin import OpsTest
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential as wexp

NHC = "lbnl-nhc-1.4.3.tar.gz"
SLURMD = "slurmd"
UNIT_0 = f"{SLURMD}/0"

"""
@mark.skip_if_deployed
async def test_build_and_deploy_fail(ops_test: OpsTest):
    """"""
    # Deploy fails due to missing nhc resource.
    slurmd_charm = await ops_test.build_charm(".")
    await ops_test.model.deploy(slurmd_charm, application_name=SLURMD, resources={"nhc": NHC})
    # issuing dummy update_status just to trigger an event
    async with ops_test.fast_forward():
        # Should block with two messages
        # slurmd/0 [idle] blocked: Missing nhc resource
        # slurmd/0 [idle] blocked: Error installing slurmd
        await ops_test.model.wait_for_idle(apps=[SLURMD], status="blocked", timeout=1000)
        assert ops_test.model.applications[SLURMD].units[0].workload_status == "blocked"
"""

@pytest.mark.abort_on_fail
@pytest.mark.skip_if_deployed
async def test_build_and_deploy_success(ops_test: OpsTest):
    """Deploy with nhc resource."""
    resources = fetch_deps()

    slurmd_charm = await ops_test.build_charm(".")
    await ops_test.model.deploy(
        slurmd_charm,
        application_name=SLURMD,
        num_units=1,
        resources=resources,
        series="focal",
    )
    # Attach the resource to the controller.
    await ops_test.juju("attach-resource", SLURMD, f"nhc={NHC}")

    # Add slurmctld relation
    await ops_test.model.add_relation(SLURMD, "slurmctld")
    
    # TODO: Fails here due to no slurmctld charm
    # juju.errors.JujuAPIError: application "slurmctld" not found

    # await ops_test.model.set_config({"custom-slurm-repo": "ppa:omnivector/osd-testing"})
    # issuing dummy update_status just to trigger an event
    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(apps=[SLURMD], status="active", timeout=1000)
        assert ops_test.model.applications[SLURMD].units[0].workload_status == "active"
