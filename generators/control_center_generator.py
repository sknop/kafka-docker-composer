from .generator import Generator

class ControlCenterGenerator(Generator):
    def __init__(self, base):
        super().__init__(base)

    def generate(self):
        base = self.base
        control_centers = []

        if base.args.control_center:
            control_center = {
                "name": "control-center",
                "hostname": "control-center",
                "container_name": "control-center",
                "image": f"{base.repository}/cp-enterprise-control-center{base.tc}:" + base.args.release,
                "depends_on_condition": base.generate_depends_on() + base.connect_containers + base.ksqldb_containers,
                "environment": {
                    "CONTROL_CENTER_BOOTSTRAP_SERVERS": base.bootstrap_servers,
                    "CONTROL_CENTER_SCHEMA_REGISTRY_URL": base.schema_registry_urls,
                    "CONTROL_CENTER_REPLICATION_FACTOR": base.replication_factor(),
                    "CONTROL_CENTER_CONNECT_CONNECT_CLUSTER": base.connect_urls,
                    "CONTROL_CENTER_KSQL_KSQL_URL": base.ksqldb_urls
                },
                "capability": [
                    "NET_ADMIN"
                ],
                "ports": {
                    9021: 9021
                }

            }

            control_centers.append(control_center)

        return control_centers
