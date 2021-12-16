# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Listen to messages coming to centos messaging
"""
import os
from pathlib import Path

import click

from packit_service_centosmsg.consumer import Consumerino


@click.command("listen-to-centos-messaging")
def listen_to_centos_messaging():
    """
    Listen to events on centos messaging and process them.
    """

    # hardcoded defaults, because env defined in docker file is not visible (maybe to openshift)
    ca_certs = Path(os.getenv("CENTOS_CA_CERTS", "/secrets/centos-server-ca.cert"))
    certfile = Path(os.getenv("CENTOS_CERTFILE", "/secrets/centos.cert"))

    centos_mqtt_client = Consumerino()
    centos_mqtt_client.consume_from_centos_messaging(
        ca_certs=ca_certs, certfile=certfile
    )
