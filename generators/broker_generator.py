from .broker_controller_generator import BrokerControllerGenerator
from constants import *


class BrokerGenerator(BrokerControllerGenerator):
    def __init__(self, base):
        super().__init__(base)

    def generate(self):
        base = self.base
        rack = 0

        brokers = []
        bootstrap_servers = []

        targets = []
        job = {
            "name": "kafka-broker",
            "scrape_interval": "5s",
            "targets": targets
        }
        base.prometheus_jobs.append(job)

        for broker_id in range(1, base.args.brokers + 1):
            port = base.next_external_broker_port()
            internal_port = base.next_internal_broker_port()
            node_id = base.next_node_id()

            broker = {}

            name = base.create_name("kafka", broker_id)
            broker["name"] = name
            broker["hostname"] = name
            broker["container_name"] = name

            targets.append(f"{name}:{JMX_PORT}")

            broker["image"] = f"{base.repository}/{base.args.kafka_container}{base.tc}:" + base.args.release

            broker["depends_on"] = base.controller_containers[:] if base.use_kraft else base.zookeeper_containers[:]
            if base.args.control_center_next_gen:
                broker["depends_on"].append("prometheus")

            jmx_port = base.next_jmx_external_port()

            broker["environment"] = {
                "KAFKA_LISTENERS": f"PLAINTEXT://{name}:{internal_port}, EXTERNAL://0.0.0.0:{port}",
                "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP": "PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT",
                "KAFKA_ADVERTISED_LISTENERS": f"PLAINTEXT://{name}:{internal_port}, EXTERNAL://localhost:{port}",
                "KAFKA_INTER_BROKER_LISTENER_NAME": "PLAINTEXT",
                "KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS": 0,
                "KAFKA_JMX_PORT": jmx_port,
                "KAFKA_JMX_HOSTNAME": "localhost",
                "KAFKA_BROKER_RACK": f"rack-{rack}",
                "KAFKA_OPTS": JMX_PROMETHEUS_JAVA_AGENT + BROKER_JMX_CONFIG,
                "KAFKA_MIN_INSYNC_REPLICAS": base.min_insync_replicas(),
                "KAFKA_CONFLUENT_CLUSTER_LINK_ENABLE": base.replication_factor() >= 3,
                "KAFKA_CONFLUENT_REPORTERS_TELEMETRY_AUTO_ENABLE": base.replication_factor() >= 3,
            }

            if not base.args.osk:
                broker["environment"]["KAFKA_CONFLUENT_LICENSE_TOPIC_REPLICATION_FACTOR"] = base.replication_factor()
                broker["environment"]["KAFKA_METRIC_REPORTERS"] = "io.confluent.metrics.reporter.ConfluentMetricsReporter"

            if base.args.control_center_next_gen:
                self.generate_c3plusplus(broker["environment"])

            controller_dict = {}

            if base.use_kraft:
                controller_dict["KAFKA_NODE_ID"] = node_id
                controller_dict["CLUSTER_ID"] = base.args.uuid
                controller_dict["KAFKA_CONTROLLER_QUORUM_VOTERS"] = base.quorum_voters
                controller_dict["KAFKA_PROCESS_ROLES"] = 'broker'
                controller_dict["KAFKA_CONTROLLER_LISTENER_NAMES"] = "CONTROLLER"
                controller_dict["KAFKA_LISTENER_SECURITY_PROTOCOL_MAP"] = \
                    "CONTROLLER:PLAINTEXT" + "," + broker["environment"]["KAFKA_LISTENER_SECURITY_PROTOCOL_MAP"]
            else:
                controller_dict["KAFKA_DEFAULT_REPLICATION_FACTOR"] = base.replication_factor()
                controller_dict["KAFKA_BROKER_ID"] = broker_id
                controller_dict["KAFKA_ZOOKEEPER_CONNECT"] = base.zookeepers
                controller_dict["KAFKA_CONFLUENT_METRICS_REPORTER_TOPIC_REPLICAS"] = base.replication_factor()

            broker["environment"].update(controller_dict)

            broker["cap_add"] = [
                "NET_ADMIN"
            ]

            broker["ports"] = {
                port: port,
                jmx_port: jmx_port,
                base.next_agent_port(): JMX_PORT,
                base.next_http_port(): 8090
            }

            broker["volumes"] = [
                LOCAL_VOLUMES + JMX_JAR_FILE + ":/tmp/" + JMX_JAR_FILE,
                LOCAL_VOLUMES + BROKER_JMX_CONFIG + ":/tmp/" + BROKER_JMX_CONFIG
            ]

            broker["healthcheck"] = {
                "test": f"{base.healthcheck_command} cluster-id --bootstrap-server localhost:{port} || exit 1",
                "interval": "10s",
                "retries": "10",
                "start_period": "20s"
            }

            brokers.append(broker)
            bootstrap_servers.append(f"{name}:{internal_port}")

            rack = base.next_rack(rack, base.args.racks)

        if base.args.brokers > 0:
            base.bootstrap_servers = ",".join(bootstrap_servers)

        base.broker_containers = [b["name"] for b in brokers]

        for broker in brokers:
            broker["environment"]["KAFKA_CONFLUENT_METRICS_REPORTER_BOOTSTRAP_SERVERS"] = base.bootstrap_servers

        for controller in base.controllers:
            controller["environment"]["KAFKA_CONFLUENT_METRICS_REPORTER_BOOTSTRAP_SERVERS"] = base.bootstrap_servers

        return brokers
