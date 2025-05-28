from .generator import Generator
from constants import *

class ConnectGenerator(Generator):
    def __init__(self, base):
        super().__init__(base)

    def generate(self):
        base = self.base
        connects = []
        targets = []
        connect_hosts = []

        job = {
            "name": "kafka-connect",
            "scrape_interval": "5s",
            "targets": targets
        }

        for connect_id in range(1, base.args.connect_instances + 1):
            port = 8082 + connect_id

            name = base.create_name("kafka-connect", connect_id)
            plugin_dirname = "connect-plugin-jars"

            connect = {
                "name": name,
                "hostname": name,
                "container_name": name,
                "image": f"{base.repository}/cp-server-connect{base.tc}:" + base.args.release,
                "depends_on_condition": base.generate_depends_on(),
                "environment": {
                    "CONNECT_REST_ADVERTISED_PORT": port,
                    "CONNECT_REST_PORT": port,
                    "CONNECT_LISTENERS": f"http://0.0.0.0:{port}",
                    "CONNECT_BOOTSTRAP_SERVERS": base.bootstrap_servers,
                    "CONNECT_REST_ADVERTISED_HOST_NAME": name,
                    "CONNECT_GROUP_ID": "kafka-connect",
                    "CONNECT_CONFIG_STORAGE_TOPIC": "_connect-configs",
                    "CONNECT_OFFSET_STORAGE_TOPIC": "_connect-offsets",
                    "CONNECT_STATUS_STORAGE_TOPIC": "_connect-status",
                    "CONNECT_KEY_CONVERTER": "org.apache.kafka.connect.storage.StringConverter",
                    "CONNECT_VALUE_CONVERTER": "io.confluent.connect.avro.AvroConverter",
                    "CONNECT_EXACTLY_ONCE_SOURCE_SUPPORT": "enabled",
                    "CONNECT_VALUE_CONVERTER_SCHEMA_REGISTRY_URL": base.schema_registry_urls,
                    "CONNECT_CONFIG_STORAGE_REPLICATION_FACTOR": base.replication_factor(),
                    "CONNECT_OFFSET_STORAGE_REPLICATION_FACTOR": base.replication_factor(),
                    "CONNECT_STATUS_STORAGE_REPLICATION_FACTOR": base.replication_factor(),
                    "CONNECT_PLUGIN_PATH": "/usr/share/java,"
                                           "/usr/share/confluent-hub-components,"
                                           f"/data/{plugin_dirname}",
                    "KAFKA_OPTS": JMX_PROMETHEUS_JAVA_AGENT + CONNECT_JMX_CONFIG
                },
                "capability": [
                    "NET_ADMIN"
                ],
                "ports": {
                    port: port
                },
                "healthcheck": {
                    "test": f"curl -fail --silent http://{name}:{port}/connectors --output /dev/null || exit 1",
                    "interval": "10s",
                    "retries": "20",
                    "start_period": "20s"
                },
                "volumes": [
                    LOCAL_VOLUMES + JMX_JAR_FILE + ":/tmp/" + JMX_JAR_FILE,
                    LOCAL_VOLUMES + CONNECT_JMX_CONFIG + ":/tmp/" + CONNECT_JMX_CONFIG,
                    LOCAL_VOLUMES + f"{plugin_dirname}:/data/{plugin_dirname}"
                ]
            }

            targets.append(f"{name}:{JMX_PORT}")
            connects.append(connect)
            connect_hosts.append(f"http://{name}:{port}")
            base.connect_containers.append(name)

        base.connect_urls = ",".join(connect_hosts)

        if base.args.connect_instances > 0:
            base.prometheus_jobs.append(job)

        return connects
