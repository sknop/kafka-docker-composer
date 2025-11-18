from .broker_controller_generator import BrokerControllerGenerator
from constants import *

class ControllerGenerator(BrokerControllerGenerator):
    def __init__(self, base):
        super().__init__(base)

    def generate(self):
        base = self.base
        rack = 0

        controllers = []
        quorum_voters = []

        targets = []
        job = {
            "name": "kafka-controller",
            "scrape_interval": "5s",
            "targets": targets
        }

        for counter in range(1, base.args.controllers + 1):
            port = base.next_internal_broker_port()
            node_id = base.next_controller_node_id()

            controller = {}

            name = base.create_name("controller", counter)
            controller["name"] = name
            controller["hostname"] = name
            controller["container_name"] = name

            targets.append(f"{name}:{JMX_PORT}")

            controller["image"] = f"{base.repository}/{base.args.kafka_container}{base.tc}:" + base.args.release

            controller["environment"] = {
                "KAFKA_NODE_ID": node_id,
                "CLUSTER_ID": base.args.uuid,
                "KAFKA_PROCESS_ROLES": "controller,broker" if base.args.shared_mode else "controller",
                "KAFKA_LISTENERS": f"CONTROLLER://{name}:{port}",
                "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP": "CONTROLLER:PLAINTEXT",
                "KAFKA_CONTROLLER_LISTENER_NAMES": "CONTROLLER",
                "KAFKA_CONTROLLER_QUORUM_VOTERS": "# Need to set #",
                "KAFKA_JMX_PORT": 9999,
                "KAFKA_JMX_HOSTNAME": name,
                "KAFKA_BROKER_RACK": f"rack-{rack}",
                "KAFKA_DEFAULT_REPLICATION_FACTOR": base.replication_factor(),
                "KAFKA_OFFSET_REPLICATION_FACTOR": base.replication_factor(),
                "KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR": base.replication_factor(),
                "KAFKA_CONFLUENT_METADATA_TOPIC_REPLICATION_FACTOR": base.replication_factor(),
                "KAFKA_CONFLUENT_BALANCER_TOPIC_REPLICATION_FACTOR": base.replication_factor(),
                "KAFKA_OPTS": JMX_PROMETHEUS_JAVA_AGENT + CONTROLLER_JMX_CONFIG
            }

            if not base.args.osk:
                controller["environment"]["KAFKA_CONFLUENT_LICENSE_TOPIC_REPLICATION_FACTOR"] = base.replication_factor()
                controller["environment"]["KAFKA_METRIC_REPORTERS"] = "io.confluent.metrics.reporter.ConfluentMetricsReporter"
                controller["environment"]["KAFKA_CONFLUENT_METRICS_REPORTER_TOPIC_REPLICAS"] = base.replication_factor()


            if base.args.control_center_next_gen:
                self.generate_c3plusplus(controller["environment"])

            if base.args.shared_mode:
                internal_port = base.next_internal_broker_port()
                external_port = base.next_external_broker_port()

                controller["environment"]["KAFKA_ADVERTISED_LISTENERS"] = \
                    f"PLAINTEXT://{name}:{internal_port}, EXTERNAL://localhost:{external_port}"
                controller["environment"]["KAFKA_LISTENERS"] = \
                    f"CONTROLLER://{name}:{port},PLAINTEXT://{name}:{internal_port},EXTERNAL://0.0.0.0:{external_port}"
                controller["environment"]["KAFKA_LISTENER_SECURITY_PROTOCOL_MAP"] = \
                    "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT"
                controller["environment"]["KAFKA_INTER_BROKER_LISTENER_NAME"] = "PLAINTEXT"

                controller["healthcheck"] = {
                    "test": f"{base.healthcheck_command} cluster-id --bootstrap-controller {name}:{port} || exit 1",
                    "interval": "10s",
                    "retries": "10",
                    "start_period": "20s"
                }

                if base.bootstrap_servers != "":
                    base.bootstrap_servers += ','
                base.bootstrap_servers += f"{name}:{internal_port}"

            if base.args.control_center_next_gen:
                controller["depends_on"] = ["prometheus"]

                # end for

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

            rack = base.next_rack(rack, base.args.racks)

        base.controller_containers = [b["name"] for b in controllers]
        base.quorum_voters = ",".join(quorum_voters)

        for controller in controllers:
            controller["environment"]["KAFKA_CONTROLLER_QUORUM_VOTERS"] = base.quorum_voters

        if base.args.controllers > 0:
            base.prometheus_jobs.append(job)

        base.controllers = controllers

        return controllers