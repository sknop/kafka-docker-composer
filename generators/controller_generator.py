from .generator import Generator
from constants import JMX_PORT, JMX_PROMETHEUS_JAVA_AGENT, CONTROLLER_JMX_CONFIG, LOCAL_VOLUMES, JMX_JAR_FILE

class ControllerGenerator(Generator):
    def __init__(self, base):
        super().__init__(base)

    def generate(self):
        rack = 0

        controllers = []
        quorum_voters = []

        targets = []
        job = {
            "name": "kafka-controller",
            "scrape_interval": "5s",
            "targets": targets
        }

        for counter in range(1, self.base.args.controllers + 1):
            port = self.base.next_internal_broker_port()
            node_id = self.base.next_node_id()

            controller = {}

            name = self.base.create_name("controller", counter)
            controller["name"] = name
            controller["hostname"] = name
            controller["container_name"] = name

            targets.append(f"{name}:{JMX_PORT}")

            controller["image"] = f"{self.base.repository}/{self.base.args.kafka_container}{self.base.tc}:" + self.base.args.release

            controller["environment"] = {
                "KAFKA_NODE_ID": node_id,
                "CLUSTER_ID": self.base.args.uuid,
                "KAFKA_PROCESS_ROLES": "controller,broker" if self.base.args.shared_mode else "controller",
                "KAFKA_LISTENERS": f"CONTROLLER://{name}:{port}",
                "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP": "CONTROLLER:PLAINTEXT",
                "KAFKA_CONTROLLER_LISTENER_NAMES": "CONTROLLER",
                "KAFKA_CONTROLLER_QUORUM_VOTERS": "# Need to set #",
                "KAFKA_JMX_PORT": 9999,
                "KAFKA_JMX_HOSTNAME": name,
                "KAFKA_BROKER_RACK": f"rack-{rack}",
                "KAFKA_DEFAULT_REPLICATION_FACTOR": self.base.replication_factor(),
                "KAFKA_OFFSET_REPLICATION_FACTOR": self.base.replication_factor(),
                "KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR": self.base.replication_factor(),
                "KAFKA_CONFLUENT_METADATA_TOPIC_REPLICATION_FACTOR": self.base.replication_factor(),
                "KAFKA_CONFLUENT_BALANCER_TOPIC_REPLICATION_FACTOR": self.base.replication_factor(),
                "KAFKA_OPTS": JMX_PROMETHEUS_JAVA_AGENT + CONTROLLER_JMX_CONFIG
            }

            if not self.base.args.osk:
                controller["environment"]["KAFKA_CONFLUENT_LICENSE_TOPIC_REPLICATION_FACTOR"] = self.base.replication_factor()
                controller["environment"]["KAFKA_METRIC_REPORTERS"] = "io.confluent.metrics.reporter.ConfluentMetricsReporter"
                controller["environment"]["KAFKA_CONFLUENT_METRICS_REPORTER_TOPIC_REPLICAS"] = self.base.replication_factor()

            if self.base.args.shared_mode:
                internal_port = self.base.next_internal_broker_port()
                external_port = self.base.next_external_broker_port()

                controller["environment"]["KAFKA_ADVERTISED_LISTENERS"] = \
                    f"PLAINTEXT://{name}:{internal_port}, EXTERNAL://localhost:{external_port}"
                controller["environment"]["KAFKA_LISTENERS"] = \
                    f"CONTROLLER://{name}:{port},PLAINTEXT://{name}:{internal_port},EXTERNAL://0.0.0.0:{external_port}"
                controller["environment"]["KAFKA_LISTENER_SECURITY_PROTOCOL_MAP"] = \
                    "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT"
                controller["environment"]["KAFKA_INTER_BROKER_LISTENER_NAME"] = "PLAINTEXT"

                controller["healthcheck"] = {
                    "test": f"{self.base.healthcheck_command} cluster-id --bootstrap-controller {name}:{port} || exit 1",
                    "interval": "10s",
                    "retries": "10",
                    "start_period": "20s"
                }

                if self.base.bootstrap_servers != "":
                    self.base.bootstrap_servers += ','
                self.base.bootstrap_servers += f"{name}:{internal_port}"

            controller["volumes"] = [
                LOCAL_VOLUMES + JMX_JAR_FILE + ":/tmp/" + JMX_JAR_FILE,
                LOCAL_VOLUMES + CONTROLLER_JMX_CONFIG + ":/tmp/" + CONTROLLER_JMX_CONFIG
            ]

            controller["cap_add"] = [
                "NET_ADMIN"
            ]

            controller["ports"] = {
                port: port
            }

            controllers.append(controller)
            quorum_voters.append(f"{node_id}@{name}:{port}")

            rack = self.base.next_rack(rack, self.base.args.racks)

        self.base.controller_containers = [b["name"] for b in controllers]
        self.base.quorum_voters = ",".join(quorum_voters)

        for controller in controllers:
            controller["environment"]["KAFKA_CONTROLLER_QUORUM_VOTERS"] = self.base.quorum_voters

        if self.base.args.controllers > 0:
            self.base.prometheus_jobs.append(job)

        self.base.controllers = controllers

        return controllers