# Centos messaging consumer for Packit Service

- Our website: [packit.dev](https://packit.dev)
- [CONTRIBUTING.md](/CONTRIBUTING.md)

## Configuration

The following environment variables can be used to configure the consumer:

### `LOG_LEVEL`

Set logging level. Set to one of the Python [logging
level](https://docs.python.org/3/library/logging.html#levels) strings.
Defaults to `INFO` if not set.

### `DISABLE_SENDING_CELERY_TASKS`

Set this to a non-empty value in order to skip creating Celery tasks in the
worker queue. This is intended to be used to debug the consumer without the
danger to create noise in the worker queue.

### `MQTT_HOST`

MQTT broker hostname. Defaults to `mqtt.stg.centos.org`.

### `MQTT_TOPICS`

Topic the consumer should listen to. Can use MQTT topic wildcards. Defaults to
`git.stg.centos.org/#`.

### `MQTT_SUBTOPICS`

Comma separated list of sub-topics to filter for. No filtering is done if not
set.

This is really just a hack, at the moment, in order to work around the fact
that `git.centos.org` has only 2 topic levels. With this variable it's
possible to filter for partial matches of the second level.

For example, setting this to `pull-request` will make the consumer handle

```
git.centos.org/pull-request.new
```

but ignore

```
git.centos.org/commit.flag.added
```

Can be a comma separated list for multiple sub-topics, for example, to handle
both messages above set:

```
MQTT_SUBTOPICS="pull-request,commit"
```

The "right" solution would be to have `git.centos.org` use proper [MQTT topic
levels](https://mosquitto.org/man/mqtt-7.html), where the topics above would
look like:

```
git.centos.org/pull-request/new
git.centos.org/commit/flag/added
```

In this case the consumer could be configured to only listen to
`git.centos.org/pull-request/#`.
