from .generator import Generator
from constants import *

class ControlCenterNextGenerationGenerator(Generator):
    def __init__(self, base):
        super().__init__(base)

    def generate(self):
        base = self.base
        control_centers = []

        if base.args.control_center_next_gen:
            control_center = {
                "name": "control-center",
                "hostname": "control-center",
                "container_name": "control-center",
                "image": f"{base.repository}/cp-enterprise-control-center-next-gen{base.tc}:" + base.args.control_center_next_gen_release,
                "depends_on_condition": base.generate_depends_on() + base.connect_containers + base.ksqldb_containers,
                "environment": {
                    "CONTROL_CENTER_BOOTSTRAP_SERVERS": base.bootstrap_servers,
                    "CONTROL_CENTER_SCHEMA_REGISTRY_URL": base.schema_registry_urls,
                    "CONTROL_CENTER_REPLICATION_FACTOR": base.replication_factor(),
                    "CONTROL_CENTER_CONNECT_CONNECT_CLUSTER": base.connect_urls,
                    "CONTROL_CENTER_CONNECT_HEALTHCHECK_ENDPOINT": "/connectors",
                    "CONTROL_CENTER_KSQL_KSQL_URL": base.ksqldb_urls,
                    "CONTROL_CENTER_PROMETHEUS_ENABLE": "true",
                    "CONTROL_CENTER_PROMETHEUS_URL": "http://prometheus:9090",
                    "CONTROL_CENTER_PROMETHEUS_RULES_FILE": "/mnt/config/trigger_rules-generated.yml",
                    "CONTROL_CENTER_ALERTMANAGER_URL": "http://alertmanager:9093",
                    "CONTROL_CENTER_ALERTMANAGER_CONFIG_FILE": "/mnt/config/alertmanager.yml",
                    "CONTROL_CENTER_CMF_URL": "http://control-center:9021"
                },
                "capability": [
                    "NET_ADMIN"
                ],
                "volumes": [
                    LOCAL_VOLUMES + "config:/mnt/config"
                ],
                "ports": {
                    9021: 9021
                }

            }

            control_centers.append(control_center)

        return control_centers
