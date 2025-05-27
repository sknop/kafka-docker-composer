from .generator import Generator
from constants import JMX_PORT, JMX_PROMETHEUS_JAVA_AGENT, LOCAL_VOLUMES, JMX_JAR_FILE, BROKER_JMX_CONFIG


class BrokerGenerator(Generator):
    def __init__(self, base):
        super().__init__(base)

    def generate(self):
        rack = 0

        brokers = []
        bootstrap_servers = []

        targets = []
        job = {
            "name": "kafka-broker",
            "scrape_interval": "5s",
            "targets": targets
        }
        self.base.prometheus_jobs.append(job)

        for broker_id in range(1, self.base.args.brokers + 1):
            port = self.base.next_external_broker_port()
            internal_port = self.base.next_internal_broker_port()
            node_id = self.base.next_node_id()

            broker = {}

            name = self.base.create_name("kafka", broker_id)
            broker["name"] = name
            broker["hostname"] = name
            broker["container_name"] = name

            targets.append(f"{name}:{JMX_PORT}")

            broker["image"] = f"{self.base.repository}/{self.base.args.kafka_container}{self.base.tc}:" + self.base.args.release

            broker["depends_on"] = self.base.controller_containers if self.base.use_kraft else self.base.zookeeper_containers

            jmx_port = self.base.next_jmx_external_port()

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
                "KAFKA_MIN_INSYNC_REPLICAS": self.base.min_insync_replicas(),
                "KAFKA_CONFLUENT_CLUSTER_LINK_ENABLE": self.base.replication_factor() >= 3,
                "KAFKA_CONFLUENT_REPORTERS_TELEMETRY_AUTO_ENABLE": self.base.replication_factor() >= 3,
            }

            if not self.base.args.osk:
                broker["environment"]["KAFKA_CONFLUENT_LICENSE_TOPIC_REPLICATION_FACTOR"] = self.base.replication_factor()
                broker["environment"]["KAFKA_METRIC_REPORTERS"] = "io.confluent.metrics.reporter.ConfluentMetricsReporter"

            controller_dict = {}

            if self.base.use_kraft:
                controller_dict["KAFKA_NODE_ID"] = node_id
                controller_dict["CLUSTER_ID"] = self.base.args.uuid
                controller_dict["KAFKA_CONTROLLER_QUORUM_VOTERS"] = self.base.quorum_voters
                controller_dict["KAFKA_PROCESS_ROLES"] = 'broker'
                controller_dict["KAFKA_CONTROLLER_LISTENER_NAMES"] = "CONTROLLER"
                controller_dict["KAFKA_LISTENER_SECURITY_PROTOCOL_MAP"] = \
                    "CONTROLLER:PLAINTEXT" + "," + broker["environment"]["KAFKA_LISTENER_SECURITY_PROTOCOL_MAP"]
            else:
                controller_dict["KAFKA_DEFAULT_REPLICATION_FACTOR"] = self.base.replication_factor()
                controller_dict["KAFKA_BROKER_ID"] = broker_id
                controller_dict["KAFKA_ZOOKEEPER_CONNECT"] = self.base.zookeepers
                controller_dict["KAFKA_CONFLUENT_METRICS_REPORTER_TOPIC_REPLICAS"] = self.base.replication_factor()

            broker["environment"].update(controller_dict)

            broker["cap_add"] = [
                "NET_ADMIN"
            ]

            broker["ports"] = {
                port: port,
                jmx_port: jmx_port,
                self.base.next_agent_port(): JMX_PORT,
                self.base.next_http_port(): 8090
            }

            broker["volumes"] = [
                LOCAL_VOLUMES + JMX_JAR_FILE + ":/tmp/" + JMX_JAR_FILE,
                LOCAL_VOLUMES + BROKER_JMX_CONFIG + ":/tmp/" + BROKER_JMX_CONFIG
            ]

            broker["healthcheck"] = {
                "test": f"{self.base.healthcheck_command} cluster-id --bootstrap-server localhost:{port} || exit 1",
                "interval": "10s",
                "retries": "10",
                "start_period": "20s"
            }

            brokers.append(broker)
            bootstrap_servers.append(f"{name}:{internal_port}")

            rack = self.base.next_rack(rack, self.base.args.racks)

        if self.base.args.brokers > 0:
            self.base.bootstrap_servers = ",".join(bootstrap_servers)

        self.base.broker_containers = [b["name"] for b in brokers]

        for broker in brokers:
            broker["environment"]["KAFKA_CONFLUENT_METRICS_REPORTER_BOOTSTRAP_SERVERS"] = self.base.bootstrap_servers

        for controller in self.base.controllers:
            controller["environment"]["KAFKA_CONFLUENT_METRICS_REPORTER_BOOTSTRAP_SERVERS"] = self.base.bootstrap_servers

        return brokers
