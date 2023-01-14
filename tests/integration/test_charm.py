#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import pytest 
import requests
import yaml

from helpers import (
    fetch_slurmd_deps,
    fetch_slurmctld_deps,
)

from pathlib import Path

from pytest_operator.plugin import OpsTest
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential as wexp

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
NHC = METADATA["resources"]["nhc"]["filename"]
ETCD = "etcd-v3.5.0-linux-amd64.tar.gz"
SERIES = ["focal"]
SLURMD = "slurmd"
SLURMDBD = "slurmdbd"
SLURMCTLD = "slurmctld"
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
@pytest.mark.parametrize("series", SERIES)
@pytest.mark.skip_if_deployed
async def test_build_and_deploy_success(ops_test: OpsTest, series: str):
    """Deploy with nhc resource."""
    res_slurmd = fetch_slurmd_deps()
    res_slurmctld = fetch_slurmctld_deps()

    # Build slurmd local charm
    slurmd_charm = await ops_test.build_charm(".")

    await asyncio.gather(
        # Fetch from charmhub slurmctld
        ops_test.model.deploy(
            SLURMCTLD,
            application_name=SLURMCTLD,
            num_units=1,
            resources=res_slurmctld,
            series=series,
        ),
        ops_test.model.deploy(
            slurmd_charm,
            application_name=SLURMD,
            num_units=1,
            resources=res_slurmd,
            series=series,
        ),
        ops_test.model.deploy(
            SLURMDBD,
            application_name=SLURMDBD,
            num_units=1,
            series=series,
        ),
        ops_test.model.deploy(
            "percona-cluster",
            application_name="mysql",
            num_units=1,
            series="bionic",
        ),
    )

    # Attach NHC resource to the slurmd controller
    await ops_test.juju("attach-resource", SLURMD, f"nhc={NHC}")

    # Attach ETCD resource to the slurmctld controller
    await ops_test.juju("attach-resource", SLURMCTLD, f"etcd={ETCD}")

    # Add slurmdbd relation to slurmctld
    await ops_test.model.add_relation(SLURMCTLD, SLURMDBD)

    # Add slurmdbd relation to slurmctld
    await ops_test.model.add_relation(SLURMDBD, "mysql")

    # Reducing the update status frequency to speed up the triggering of deferred events.
    await ops_test.model.set_config({"update-status-hook-interval": "10s"})

    # TODO: It's possible for slurmd to be stuck waiting for slurmctld despite slurmctld and slurmdbd
    # available. Relation between slurmd and slurmctld has to be added after slurmctld is ready.

    # Wait for slurmdbd and slurmctld to be ready
    await ops_test.model.wait_for_idle(apps=[SLURMDBD, SLURMCTLD], status="active", timeout=1000)

    # Add slurmctld relation to slurmd
    await ops_test.model.add_relation(SLURMD, SLURMCTLD)

    # await ops_test.model.set_config({"custom-slurm-repo": "ppa:omnivector/osd-testing"})
    # issuing dummy update_status just to trigger an event
    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(apps=[SLURMD], status="active", timeout=1000)
        assert ops_test.model.applications[SLURMD].units[0].workload_status == "active"
