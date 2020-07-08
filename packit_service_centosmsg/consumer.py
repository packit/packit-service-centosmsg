# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import os
import ssl
import logging
from pathlib import Path

import paho.mqtt.client as mqtt
from celery import Celery

logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


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
            password = os.getenv("REDIS_PASSWORD", "")
            host = os.getenv("REDIS_SERVICE_HOST", "redis")
            port = os.getenv("REDIS_SERVICE_PORT", "6379")
            db = os.getenv("REDIS_SERVICE_DB", "0")
            redis_url = f"redis://:{password}@{host}:{port}/{db}"

            self._celery_app = Celery(backend=redis_url, broker=redis_url)
        return self._celery_app

    def on_message(self, client, userdata, msg):
        logger.info(f"Received a message on topic: {msg.topic}")
        subtopic = msg.topic.split("/", 1)[-1].split(".", 1)[0]
        if self.subtopics and subtopic not in self.subtopics:
            logger.info(
                f"Ignore message: Subtopic {subtopic!r} not in {self.subtopics!r}."
            )
            return

        message = json.loads(msg.payload)
        message["topic"] = msg.topic
        logger.debug(json.dumps(message, indent=4))

        if self.disable_sending_celery_tasks:
            logger.info("Skip sending Celery task.")
            return

        result = self.celery_app.send_task(
            name="task.steve_jobs.process_message",
            kwargs={"event": message, "source": "centosmsg"},
        )
        logger.info(f"Task UUID={result.id} sent to Celery.")

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected with result code: {rc}")
        self.disable_sending_celery_tasks = os.getenv(
            "DISABLE_SENDING_CELERY_TASKS", False
        )
        # TODO(csomh): try to make it a comma separated list of topics
        topic = os.getenv("MQTT_TOPICS", "git.stg.centos.org/#")
        # TODO(csomh): do we need a more flexible way to define sub-topics?
        self.subtopics = [x for x in os.getenv("MQTT_SUBTOPICS", "").split(",") if x]
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
        host = os.getenv("MQTT_HOST", "mqtt.stg.centos.org")
        port = int(os.getenv("MQTT_PORT", 8883))
        self.connect(host=host, port=port)
        logger.info(f"Connected to {host}:{port}")
        self.loop_forever()
