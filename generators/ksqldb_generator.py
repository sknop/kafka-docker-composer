from .generator import Generator
from constants import *

class KSQLDBGenerator(Generator):
    def __init__(self, base):
        super().__init__(base)

    def generate(self):
        base = self.base
        ksqldbs = []
        targets = []
        ksqldb_hosts = []

        job = {
            "name": "ksqldb",
            "scrape_interval": "5s",
            "targets": targets
        }

        for ksqldb_id in range(1, base.args.ksqldb_instances + 1):
            port = 8087 + ksqldb_id

            name = base.create_name("ksqldb", ksqldb_id)

            # No base.tc since the underlying image cannot be built

            ksqldb = {
                'name': name,
                "hostname": name,
                "container_name": name,
                "image": f"confluentinc/cp-ksqldb-server:" + base.args.release,
                "depends_on_condition": base.generate_depends_on(),
                "environment": {
                    "KSQL_LISTENERS": f"http://0.0.0.0:{port}",
                    "KSQL_BOOTSTRAP_SERVERS": base.bootstrap_servers,
                    "KSQL_KSQL_LOGGING_PROCESSING_STREAM_AUTO_CREATE": "true",
                    "KSQL_KSQL_LOGGING_PROCESSING_TOPIC_AUTO_CREATE": "true",
                    "KSQL_KSQL_CONNECT_URL": base.connect_urls,
                    "KSQL_KSQL_SCHEMA_REGISTRY_URL": base.schema_registry_urls,
                    "KSQL_KSQL_SERVICE_ID": "kafka-docker-composer",
                    "KSQL_KSQL_HIDDEN_TOPICS": "^_.*",
                    "KSQL_KSQL_INTERNAL_TOPICS_REPLICAS": base.replication_factor(),
                    "KSQL_KSQL_LOGGING_PROCESSING_TOPIC_REPLICATION_FACTOR": base.replication_factor(),
                },
                "capability": [
                    "NET_ADMIN"
                ],
                "ports": {
                    port: port
                },
                "healthcheck": {
                    "test": f"curl -fail --silent http://{name}:{port}/healthcheck --output /dev/null || exit 1",
                    "interval": "10s",
                    "retries": "20",
                    "start_period": "20s"
                },
                "volumes": [
                    LOCAL_VOLUMES + JMX_JAR_FILE + ":/tmp/" + JMX_JAR_FILE
                ]
            }

            ksqldbs.append(ksqldb)
            ksqldb_hosts.append(f"http://{name}:{port}")
            base.ksqldb_containers.append(name)

        base.ksqldb_urls = ",".join(ksqldb_hosts)

        return ksqldbs
