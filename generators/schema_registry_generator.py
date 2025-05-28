from .generator import Generator
from constants import *

class SchemaRegistryGenerator(Generator):
    def __init__(self,base):
        super().__init__(base)

    def generate(self):
        base = self.base
        schema_registries = []

        schema_registry_hosts = []
        schema_registry_urls = []
        targets = []
        job = {
            "name": "schema-registry",
            "scrape_interval": "5s",
            "targets": targets
        }

        for schema_id in range(1, base.args.schema_registries + 1):
            port = 8080 + schema_id

            name = base.create_name("schema-registry", schema_id)

            schema_registry = {
                "name": name,
                "hostname": name,
                "container_name": name,
                "image": f"{base.repository}/cp-schema-registry{base.tc}:" + base.args.release,
                "depends_on_condition": base.generate_depends_on(),
                "environment": {
                    "SCHEMA_REGISTRY_HOST_NAME": name,
                    "SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS": base.bootstrap_servers,
                    "SCHEMA_REGISTRY_LISTENERS": f"http://0.0.0.0:{port}",
                    "SCHEMA_REGISTRY_OPTS": JMX_PROMETHEUS_JAVA_AGENT + SCHEMA_REGISTRY_JMX_CONFIG
                },
                "capability": [
                    "NET_ADMIN"
                ],
                "ports": {
                    port: port
                },
                "healthcheck": {
                    "test": f"curl -fail --silent http://{name}:{port}/subjects --output /dev/null || exit 1",
                    "interval": "10s",
                    "retries": "20",
                    "start_period": "20s"
                },
                "volumes": [
                    LOCAL_VOLUMES + JMX_JAR_FILE + ":/tmp/" + JMX_JAR_FILE,
                    LOCAL_VOLUMES + SCHEMA_REGISTRY_JMX_CONFIG + ":/tmp/" + SCHEMA_REGISTRY_JMX_CONFIG
                ]
            }

            targets.append(f"{name}:{JMX_PORT}")

            schema_registries.append(schema_registry)
            schema_registry_hosts.append(f"{name}:{port}")
            schema_registry_urls.append(f"http://{name}:{port}")

            base.schema_registry_containers.append(name)

        base.schema_registries = ",".join(schema_registry_hosts)
        base.schema_registry_urls = ",".join(schema_registry_urls)

        if base.args.schema_registries > 0:
            base.prometheus_jobs.append(job)

        return schema_registries
