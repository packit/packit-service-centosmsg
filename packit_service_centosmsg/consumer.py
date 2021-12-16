# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import json
import logging
import ssl
from os import getenv
from pathlib import Path

import paho.mqtt.client as mqtt
from celery import Celery

logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)
logger.setLevel(getenv("LOG_LEVEL", "INFO"))


class Consumerino(mqtt.Client):
    """
    Consume events from centos messaging
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._celery_app = None
        self.subtopics = None
        self.disable_sending_celery_tasks = False

    @property
    def celery_app(self):
        if self._celery_app is None:
            host = getenv("REDIS_SERVICE_HOST", "redis")
            password = getenv("REDIS_PASSWORD", "")
            port = getenv("REDIS_SERVICE_PORT", "6379")
            db = getenv("REDIS_SERVICE_DB", "0")
            broker_url = f"redis://:{password}@{host}:{port}/{db}"
            logger.debug(f"Celery uses {broker_url}")

            self._celery_app = Celery(broker=broker_url)
            if getenv("CELERY_DEFAULT_QUEUE"):
                self._celery_app.conf.task_default_queue = getenv(
                    "CELERY_DEFAULT_QUEUE"
                )
        return self._celery_app

    def on_message(self, client, userdata, msg):
        logger.info(f"Received a message on topic: {msg.topic}")
        received_subtopic = msg.topic.split("/", 1)[-1]
        if self.subtopics and not any(
            received_subtopic.startswith(subtopic) for subtopic in self.subtopics
        ):
            logger.info(
                f"Ignore message: Subtopic {received_subtopic!r} not in {self.subtopics!r}."
            )
            return

        message = json.loads(msg.payload)
        message["topic"] = msg.topic
        logger.debug(json.dumps(message, indent=4))

        if self.disable_sending_celery_tasks:
            logger.info("Skip sending Celery task.")
            return

        result = self.celery_app.send_task(
            name=getenv("CELERY_TASK_NAME", "task.steve_jobs.process_message"),
            kwargs={"event": message, "source": "centosmsg"},
        )
        logger.info(f"Task UUID={result.id} sent to Celery.")

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected with result code: {rc}")
        self.disable_sending_celery_tasks = getenv(
            "DISABLE_SENDING_CELERY_TASKS", False
        )
        # TODO(csomh): try to make it a comma separated list of topics
        topic = getenv("MQTT_TOPICS", "git.stg.centos.org/#")
        # TODO(csomh): do we need a more flexible way to define sub-topics?
        self.subtopics = [x for x in getenv("MQTT_SUBTOPICS", "").split(",") if x]
        logger.info(f"Subscribing to topics: {topic!r}")
        logger.info(f"Filtering for the following subtopics: {self.subtopics!r}")
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe(topic)

    def consume_from_centos_messaging(self, ca_certs: Path, certfile: Path):
        if not ca_certs.is_file():
            raise FileNotFoundError(f'"{ca_certs}" is not a file.')

        if not certfile.is_file():
            raise FileNotFoundError(f'"{certfile}" is not a file.')

        self.tls_set(
            ca_certs=str(ca_certs),
            certfile=certfile,
            keyfile=certfile,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS,
        )
        host = getenv("MQTT_HOST", "mqtt.stg.centos.org")
        port = int(getenv("MQTT_PORT", 8883))
        self.connect(host=host, port=port)
        logger.info(f"Connected to {host}:{port}")
        self.loop_forever()
