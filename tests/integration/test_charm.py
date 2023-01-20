#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import pytest
import requests
import time
import yaml

from helpers import (
    fetch_slurmd_deps,
    fetch_slurmctld_deps,
)

from subprocess import PIPE, check_output

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


@pytest.mark.abort_on_fail
@pytest.mark.parametrize("series", SERIES)
@pytest.mark.skip_if_deployed
async def test_build_and_deploy_success(ops_test: OpsTest, series: str, slurmd_charm):
    """Deploy with nhc resource."""
    res_slurmd = fetch_slurmd_deps()
    res_slurmctld = fetch_slurmctld_deps()

    charm = await slurmd_charm

    await asyncio.gather(
        # Fetch from charmhub slurmctld
        ops_test.model.deploy(
            SLURMCTLD,
            application_name=SLURMCTLD,
            channel="edge",
            num_units=1,
            resources=res_slurmctld,
            series=series,
        ),
        ops_test.model.deploy(
            charm,
            application_name=SLURMD,
            num_units=1,
            resources=res_slurmd,
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
    await ops_test.juju("attach-resource", SLURMCTLD, f"etcd={ETCD}")

    # Add slurmdbd relation to slurmctld
    await ops_test.model.relate(SLURMCTLD, SLURMDBD)

    # Add mysql relation to slurmdbd
    await ops_test.model.relate(SLURMDBD, "mysql")

    # TODO: It's possible for slurmd to be stuck waiting for slurmctld despite slurmctld and slurmdbd
    # available. Relation between slurmd and slurmctld has to be added after slurmctld is ready.

    # Attach NHC resource to the slurmd controller
    await ops_test.juju("attach-resource", SLURMD, f"nhc={NHC}")

    # Add slurmctld relation to slurmd
    await ops_test.model.relate(SLURMD, SLURMCTLD)

    # issuing dummy update_status just to trigger an event
    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(apps=[SLURMD], status="active", timeout=1000)
        assert ops_test.model.applications[SLURMD].units[0].workload_status == "active"

@pytest.mark.abort_on_fail
async def test_mpi_install(ops_test: OpsTest):
    unit = ops_test.model.applications[SLURMD].units[0]
    action = await unit.run_action("mpi-install")
    result = await action.wait()
    result = check_output(
        f"JUJU_MODEL={ops_test.model_full_name} juju exec --unit slurmd/0 mpirun --version",
        stderr=PIPE,
        shell=True,
        universal_newlines=True,
    )
    time.sleep(5)  # Wait 
    assert "buckets" in result

"""
@pytest.mark.abort_on_fail
@retry(wait=wexp(multiplier=2, min=1, max=30), stop=stop_after_attempt(10), reraise=True)
async def test_application_is_up(ops_test: OpsTest):
    status = await ops_test.model.get_status() 
    unit = list(status.applications[SLURMCTLD].units)[0]
    address = status["applications"][SLURMCTLD]["units"][unit]["public-address"]
    # Test ETCD3
    response = requests.get(f"http://{address}:2379/v3/")
    assert response.status_code == 200
    # response = requests.get(f"http://{address}:6818/metrics")
    # assert response.status_code == 200
"""
