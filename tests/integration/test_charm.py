#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test slurmd charm against other SLURM charms in the latest/edge channel."""

import asyncio
import pytest

from helpers import (
    get_slurmd_res,
    get_slurmctld_res,
)

from pathlib import Path
from pytest_operator.plugin import OpsTest
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential as wexp

SERIES = ["focal"]
SLURMD = "slurmd"
SLURMDBD = "slurmdbd"
SLURMCTLD = "slurmctld"


@pytest.mark.abort_on_fail
@pytest.mark.parametrize("series", SERIES)
@pytest.mark.skip_if_deployed
async def test_build_and_deploy(ops_test: OpsTest, series: str, slurmd_charm):
    """Test that the slurmd charm can stabilize against slurmctld, slurmdbd and percona."""
    res_slurmd = get_slurmd_res()
    res_slurmctld = get_slurmctld_res()

    # Fetch edge from charmhub for slurmctld, slurmdbd and percona and deploy
    await asyncio.gather(
        ops_test.model.deploy(
            SLURMCTLD,
            application_name=SLURMCTLD,
            channel="edge",
            num_units=1,
            resources=res_slurmctld,
            series=series,
        ),
        ops_test.model.deploy(
            SLURMDBD,
            application_name=SLURMDBD,
            channel="edge",
            num_units=1,
            series=series,
        ),
        ops_test.model.deploy(
            "percona-cluster",
            application_name="mysql",
            channel="edge",
            num_units=1,
            series="bionic",
        ),
    )

    # Attach ETCD resource to the slurmctld controller
    await ops_test.juju("attach-resource", SLURMCTLD, f"etcd={res_slurmctld['etcd']}")

    # Add slurmdbd integration to slurmctld
    await ops_test.model.relate(SLURMCTLD, SLURMDBD)

    # Add mysql integration to slurmdbd
    await ops_test.model.relate(SLURMDBD, "mysql")

    # IMPORTANT: It's possible for slurmd to be stuck waiting for slurmctld despite slurmctld and slurmdbd
    # available. Relation between slurmd and slurmctld has to be added after slurmctld is ready
    # otherwise risk running into race-condition type behavior.
    await ops_test.model.wait_for_idle(apps=[SLURMCTLD], status="blocked", timeout=1000)

    # Build and Deploy Slurmd
    charm = await slurmd_charm
    await ops_test.model.deploy(
            charm,
            application_name=SLURMD,
            num_units=1,
            resources=res_slurmd,
            series=series,
    )

    # Attach NHC resource to the slurmd controller
    await ops_test.juju("attach-resource", SLURMD, f"nhc={res_slurmd['nhc']}")

    # Add slurmctld integration to slurmd
    await ops_test.model.relate(SLURMD, SLURMCTLD)

    # Reduce the update status frequency to accelerate the triggering of deferred events.
    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(apps=[SLURMD], status="active", timeout=1000)
        assert ops_test.model.applications[SLURMD].units[0].workload_status == "active"


async def test_mpi_install(ops_test: OpsTest):
    "That that mpi is installed."
    unit = ops_test.model.applications[SLURMD].units[0]
    action = await unit.run_action("mpi-install")
    action_res = await action.wait()
    assert "installation" in action_res.results.keys()
    cmd_res = (await unit.ssh(command="mpirun --version")).strip("\n")
    assert "Version:" in cmd_res


async def test_slurmd_is_active(ops_test: OpsTest):
    """Test that slurmd is active."""
    unit = ops_test.model.applications[SLURMD].units[0]
    cmd_res = (await unit.ssh(command="systemctl is-active slurmd")).strip("\n")
    assert cmd_res == "active"


async def test_munge_is_active(ops_test: OpsTest):
    """Test that munge is active."""
    unit = ops_test.model.applications[SLURMD].units[0]
    cmd_res = (await unit.ssh(command="systemctl is-active munge")).strip("\n")
    assert cmd_res == "active"
