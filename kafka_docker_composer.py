import argparse
import sys

import configparser

from jinja2 import Environment, PackageLoader, select_autoescape

# constants

RANDOM_UUID = "Nk018hRAQFytWskYqtQduw"

DEFAULT_RELEASE = "7.5.0"
JMX_PROMETHEUS_JAVA_AGENT_VERSION = "0.19.0"
JMX_PORT = "8091"
JMX_JAR_FILE = f"jmx_prometheus_javaagent-{JMX_PROMETHEUS_JAVA_AGENT_VERSION}.jar"
JMX_PROMETHEUS_JAVA_AGENT = f"-javaagent:/tmp/{JMX_JAR_FILE}={JMX_PORT}:/tmp/"
JMX_EXTERNAL_PORT = 10000
JMX_AGENT_PORT = 10100

BROKER_EXTERNAL_BASE_PORT = 9090
BROKER_INTERNAL_BASE_PORT = 19090

LOCAL_VOLUMES = "$PWD/volumes/"

DOCKER_COMPOSE_FILE = "docker-compose.yaml"
KAFKA_CONTAINER = "cp-server"

ZOOKEEPER_JMX_CONFIG = "zookeeper_config.yml"
ZOOKEEPER_PORT = "2181"

BROKER_JMX_CONFIG = "kafka_config.yml"
SCHEMA_REGISTRY_JMX_CONFIG = "schema-registry.yml"
CONNECT_JMX_CONFIG = "kafka_connect.yml"


class DockerComposeGenerator:
    def __init__(self, arguments):
        self.args = arguments

        self.env = Environment(
            loader=PackageLoader("docker-generator"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )

        self.zookeepers = ""
        self.quorum_voters = ""
        self.bootstrap_servers = ""
        self.schema_registries = ""
        self.schema_registry_urls = ""
        self.connect_urls = ""

        self.controllers = []

        self.controller_containers = []
        self.zookeeper_containers = []
        self.broker_containers = []
        self.connect_containers = []
        self.schema_registry_containers = []

        self.prometheus_jobs = []

        self.jmx_external_port_counter = JMX_EXTERNAL_PORT
        self.agent_port_counter = JMX_AGENT_PORT

        self.use_kraft = self.args.controllers > 0
        self.node_id = 0
        self.internal_port = BROKER_INTERNAL_BASE_PORT
        self.external_port = BROKER_EXTERNAL_BASE_PORT

    def next_jmx_external_port(self):
        self.jmx_external_port_counter += 1
        return self.jmx_external_port_counter

    def next_agent_port(self):
        self.agent_port_counter += 1
        return self.agent_port_counter

    def next_node_id(self):
        self.node_id += 1
        return self.node_id

    def next_internal_broker_port(self):
        self.internal_port += 1
        return self.internal_port

    def next_external_broker_port(self):
        self.external_port += 1
        return self.external_port

    def generate(self):
        self.generate_services()
        self.generate_prometheus()

    def replication_factor(self):
        return min(3, self.args.brokers)

    def min_insync_replicas(self):
        return max(1, self.replication_factor() - 1)

    def generate_services(self):
        services = []
        services += self.generate_zookeeper_services()
        services += self.generate_controller_services()
        services += self.generate_broker_services()
        services += self.generate_schema_registry_service()
        services += self.generate_connect_services()
        services += self.generate_control_center_service()
        services += self.generate_prometheus_service()
        services += self.generate_grafana_service()
        variables = {
            "docker_compose_version": "3.8",
            "services": services
        }

        template = self.env.get_template('docker-compose.j2')
        result = template.render(variables)

        with open(self.args.docker_compose_file, "w") as yaml_file:
            yaml_file.write(result)

    def generate_prometheus(self):
        template = self.env.get_template('prometheus.j2')

        variables = {
            "jobs": self.prometheus_jobs
        }
        result = template.render(variables)

        with open('volumes/prometheus.yml', "w") as yaml_file:
            yaml_file.write(result)

    @staticmethod
    def create_name(basename, counter):
        return f"{basename}-{counter}"

    def generate_controller_services(self):
        rack = 0

        controllers = []
        quorum_voters = []

        for counter in range(1, self.args.controllers + 1):
            port = self.next_internal_broker_port()
            node_id = self.next_node_id()

            controller = {}

            name = self.create_name("controller", counter)
            controller["name"] = name
            controller["hostname"] = name
            controller["container_name"] = name

            controller["image"] = f"confluentinc/{KAFKA_CONTAINER}:" + self.args.release

            controller["environment"] = {
                "KAFKA_NODE_ID": node_id,
                "CLUSTER_ID": self.args.uuid,
                "KAFKA_PROCESS_ROLES": "controller",
                "KAFKA_LISTENERS": f"CONTROLLER://{name}:{port}",
                "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP": "CONTROLLER:PLAINTEXT",
                "KAFKA_INTER_BROKER_LISTENER_NAME": "CONTROLLER",
                "KAFKA_CONTROLLER_LISTENER_NAMES": "CONTROLLER",
                "KAFKA_CONTROLLER_QUORUM_VOTERS": "# Need to set #",
                "KAFKA_JMX_PORT": 9999,
                "KAFKA_JMX_HOSTNAME": name,
                "KAFKA_BROKER_RACK": f"rack-{rack}",
                "KAFKA_DEFAULT_REPLICATION_FACTOR": self.replication_factor(),
                "KAFKA_OPTS": JMX_PROMETHEUS_JAVA_AGENT + BROKER_JMX_CONFIG
            }

            controller["volumes"] = [
                LOCAL_VOLUMES + JMX_JAR_FILE + ":/tmp/" + JMX_JAR_FILE,
                LOCAL_VOLUMES + BROKER_JMX_CONFIG + ":/tmp/" + BROKER_JMX_CONFIG
            ]

            controller["cap_add"] = [
                "NET_ADMIN"
            ]

            controller["ports"] = {
                port: port
            }

            controllers.append(controller)
            quorum_voters.append(f"{node_id}@{name}:{port}")

            rack = DockerComposeGenerator.next_rack(rack, self.args.racks)

        self.controller_containers = [b["name"] for b in controllers]
        self.quorum_voters = ",".join(quorum_voters)

        for controller in controllers:
            controller["environment"]["KAFKA_CONTROLLER_QUORUM_VOTERS"] = self.quorum_voters

        self.controllers = controllers

        return controllers

    def calculate_zookeeper_groups(self):
        zookeeper_groups = ""
        if self.args.zookeeper_groups > 1:
            zookeepers_per_group = self.args.zookeepers // self.args.zookeeper_groups
            rest = self.args.zookeepers % self.args.zookeeper_groups
            if rest != 0:
                print("ERROR, no equal distribution of zookeeper nodes across groups #ZK {} #GR {} rest {} "
                      .format(self.args.zookeepers, self.args.zookeeper_groups, rest))
                sys.exit(-1)

            groups = []
            for group in range(self.args.zookeeper_groups):
                zks = ":".join([str(1 + x + group * zookeepers_per_group) for x in range(zookeepers_per_group)])
                groups.append(zks)

            zookeeper_groups = ";".join(groups)

        return zookeeper_groups

    def generate_zookeeper_services(self):
        zookeeper_groups = self.calculate_zookeeper_groups()

        zookeepers = []
        zookeeper_servers = []

        targets = []
        job = {
            "name": "zookeeper",
            "scrape_interval": "5s",
            "targets": targets
        }

        for zk in range(1, self.args.zookeepers + 1):
            zookeeper_external_port = 2180 + zk

            zookeeper = {}

            name = self.create_name("zookeeper", zk)
            zookeeper["name"] = name
            zookeeper["hostname"] = name
            zookeeper["container_name"] = name

            targets.append(f"{name}:{JMX_PORT}")

            zookeeper_servers.append(name + ":2888:3888")

            zookeeper["image"] = "confluentinc/cp-zookeeper:" + self.args.release

            jmx_port = self.next_jmx_external_port()

            environment = {
                "ZOOKEEPER_SERVER_ID": zk,
                "ZOOKEEPER_CLIENT_PORT": ZOOKEEPER_PORT,
                "ZOOKEEPER_TICK_TIME": 2000,
                "KAFKA_JMX_PORT": jmx_port,
                "KAFKA_JMX_HOSTNAME": "localhost",
                "KAFKA_OPTS": JMX_PROMETHEUS_JAVA_AGENT + ZOOKEEPER_JMX_CONFIG
            }

            if self.args.zookeeper_groups > 1:
                environment["ZOOKEEPER_GROUPS"] = zookeeper_groups

            zookeeper["environment"] = environment

            zookeeper["volumes"] = [
                LOCAL_VOLUMES + JMX_JAR_FILE + ":/tmp/" + JMX_JAR_FILE,
                LOCAL_VOLUMES + ZOOKEEPER_JMX_CONFIG + ":/tmp/" + ZOOKEEPER_JMX_CONFIG,
                LOCAL_VOLUMES + "jline-2.14.6.jar" + ":/usr/share/java/kafka/jline-2.14.6.jar"
            ]

            zookeeper["cap_add"] = [
                "NET_ADMIN"
            ]

            zookeeper["ports"] = {
                zookeeper_external_port: ZOOKEEPER_PORT,
                jmx_port: jmx_port,
                self.next_agent_port(): JMX_PORT
            }

            zookeepers.append(zookeeper)

        zk_servers = ";".join(zookeeper_servers)
        for zk in zookeepers:
            zk["environment"]["ZOOKEEPER_SERVERS"] = zk_servers

        self.zookeepers = ",".join([z["name"] + ":" + ZOOKEEPER_PORT for z in zookeepers])

        self.zookeeper_containers = [z["name"] for z in zookeepers]

        if self.args.zookeepers > 0:
            self.prometheus_jobs.append(job)

        return zookeepers

    def generate_broker_services(self):
        rack = 0

        brokers = []
        bootstrap_servers = []

        targets = []
        job = {
            "name": "kafka-broker",
            "scrape_interval": "5s",
            "targets": targets
        }
        self.prometheus_jobs.append(job)

        for broker_id in range(1, self.args.brokers + 1):
            port = self.next_external_broker_port()
            internal_port = self.next_internal_broker_port()
            node_id = self.next_node_id()

            broker = {}

            name = self.create_name("kafka", broker_id)
            broker["name"] = name
            broker["hostname"] = name
            broker["container_name"] = name

            targets.append(f"{name}:{JMX_PORT}")

            broker["image"] = f"confluentinc/{KAFKA_CONTAINER}:" + self.args.release

            broker["depends_on"] = self.controller_containers if self.use_kraft else self.zookeeper_containers

            jmx_port = self.next_jmx_external_port()

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
                "KAFKA_MIN_INSYNC_REPLICAS": self.min_insync_replicas(),
                "KAFKA_METRIC_REPORTERS": "io.confluent.metrics.reporter.ConfluentMetricsReporter",
            }

            controller_dict = {}

            if self.use_kraft:
                controller_dict["KAFKA_NODE_ID"] = node_id
                controller_dict["CLUSTER_ID"] = self.args.uuid
                controller_dict["KAFKA_CONTROLLER_QUORUM_VOTERS"] = self.quorum_voters
                controller_dict["KAFKA_PROCESS_ROLES"] = 'broker'
                controller_dict["KAFKA_CONTROLLER_LISTENER_NAMES"] = "CONTROLLER"
                controller_dict["KAFKA_LISTENER_SECURITY_PROTOCOL_MAP"] = \
                    "CONTROLLER:PLAINTEXT" + "," + broker["environment"]["KAFKA_LISTENER_SECURITY_PROTOCOL_MAP"]
            else:
                controller_dict["KAFKA_DEFAULT_REPLICATION_FACTOR"] = self.replication_factor()
                controller_dict["KAFKA_BROKER_ID"] = broker_id
                controller_dict["KAFKA_ZOOKEEPER_CONNECT"] = self.zookeepers

            broker["environment"].update(controller_dict)

            broker["cap_add"] = [
                "NET_ADMIN"
            ]

            broker["ports"] = {
                port: port,
                jmx_port: jmx_port,
                self.next_agent_port(): JMX_PORT
            }

            broker["volumes"] = [
                LOCAL_VOLUMES + JMX_JAR_FILE + ":/tmp/" + JMX_JAR_FILE,
                LOCAL_VOLUMES + BROKER_JMX_CONFIG + ":/tmp/" + BROKER_JMX_CONFIG
            ]

            broker["healthcheck"] = {
                "test": f"curl -fail --silent http://{name}:8090/kafka/v3/clusters/ --output /dev/null || exit 1",
                "interval": "10s",
                "retries": "10",
                "start_period": "20s"
            }

            brokers.append(broker)
            bootstrap_servers.append(f"{name}:{internal_port}")

            rack = DockerComposeGenerator.next_rack(rack, self.args.racks)

        self.bootstrap_servers = ",".join(bootstrap_servers)
        self.broker_containers = [b["name"] for b in brokers]

        for broker in brokers:
            broker["environment"]["KAFKA_CONFLUENT_METRICS_REPORTER_BOOTSTRAP_SERVERS"] = \
                self.bootstrap_servers

        for controller in self.controllers:
            controller["environment"]["KAFKA_CONFLUENT_METRICS_REPORTER_BOOTSTRAP_SERVERS"] = \
                self.bootstrap_servers

        return brokers

    def generate_schema_registry_service(self):
        schema_registries = []

        schema_registry_hosts = []
        schema_registry_urls = []
        targets = []
        job = {
            "name": "schema-registry",
            "scrape_interval": "5s",
            "targets": targets
        }

        for schema_id in range(1, self.args.schema_registries + 1):
            port = 8080 + schema_id

            name = self.create_name("schema-registry", schema_id)

            schema_registry = {
                "name": name,
                "hostname": name,
                "container_name": name,
                "image": "confluentinc/cp-schema-registry:" + self.args.release,
                "depends_on_condition": self.broker_containers + self.schema_registry_containers,
                "environment": {
                    "SCHEMA_REGISTRY_HOST_NAME": name,
                    "SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS": self.bootstrap_servers,
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

            self.schema_registry_containers.append(name)

        self.schema_registries = ",".join(schema_registry_hosts)
        self.schema_registry_urls = ",".join(schema_registry_urls)

        if self.args.schema_registries > 0:
            self.prometheus_jobs.append(job)

        return schema_registries

    def generate_connect_services(self):
        connects = []
        targets = []
        connect_hosts = []

        job = {
            "name": "kafka-connect",
            "scrape_interval": "5s",
            "targets": targets
        }

        for connect_id in range(1, self.args.connect_instances + 1):
            port = 8082 + connect_id

            name = self.create_name("kafka-connect", connect_id)
            plugin_dirname = "connect-plugin-jars"

            connect = {
                "name": name,
                "hostname": name,
                "container_name": name,
                "image": "confluentinc/cp-server-connect:" + self.args.release,
                "depends_on_condition": self.broker_containers + self.schema_registry_containers,
                "environment": {
                    "CONNECT_REST_ADVERTISED_PORT": port,
                    "CONNECT_REST_PORT": port,
                    "CONNECT_LISTENERS": f"http://0.0.0.0:{port}",
                    "CONNECT_BOOTSTRAP_SERVERS": self.bootstrap_servers,
                    "CONNECT_REST_ADVERTISED_HOST_NAME": name,
                    "CONNECT_GROUP_ID": "kafka-connect",
                    "CONNECT_CONFIG_STORAGE_TOPIC": "_connect-configs",
                    "CONNECT_OFFSET_STORAGE_TOPIC": "_connect-offsets",
                    "CONNECT_STATUS_STORAGE_TOPIC": "_connect-status",
                    "CONNECT_KEY_CONVERTER": "org.apache.kafka.connect.storage.StringConverter",
                    "CONNECT_VALUE_CONVERTER": "io.confluent.connect.avro.AvroConverter",
                    "CONNECT_EXACTLY_ONCE_SOURCE_SUPPORT": "enabled",
                    "CONNECT_VALUE_CONVERTER_SCHEMA_REGISTRY_URL": self.schema_registry_urls,
                    "CONNECT_CONFIG_STORAGE_REPLICATION_FACTOR": self.replication_factor(),
                    "CONNECT_OFFSET_STORAGE_REPLICATION_FACTOR": self.replication_factor(),
                    "CONNECT_STATUS_STORAGE_REPLICATION_FACTOR": self.replication_factor(),
                    "CONNECT_PLUGIN_PATH": "/usr/share/java,"
                                           "/usr/share/confluent-hub-components,"
                                           f"/data/{plugin_dirname}",
                    "KAFKA_OPTS": JMX_PROMETHEUS_JAVA_AGENT + CONNECT_JMX_CONFIG
                },
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
            self.connect_containers.append(name)

        self.connect_urls = ",".join(connect_hosts)

        return connects

    def generate_control_center_service(self):
        control_centers = []

        if self.args.control_center:
            control_center = {
                "name": "control-center",
                "hostname": "control-center",
                "container_name": "control-center",
                "image": "confluentinc/cp-enterprise-control-center:" + self.args.release,
                "depends_on_condition":
                    self.broker_containers + self.schema_registry_containers + self.connect_containers,
                "environment": {
                    "CONTROL_CENTER_BOOTSTRAP_SERVERS": self.bootstrap_servers,
                    "CONTROL_CENTER_SCHEMA_REGISTRY_URL": self.schema_registry_urls,
                    "CONTROL_CENTER_REPLICATION_FACTOR": self.replication_factor(),
                    "CONTROL_CENTER_CONNECT_CONNECT_CLUSTER": self.connect_urls
                },
                "ports": {
                    9021: 9021
                }

            }

            control_centers.append(control_center)

        return control_centers

    def generate_prometheus_service(self):
        proms = []
        if self.args.prometheus:
            prometheus = {
                "name": "prometheus",
                "hostname": "prometheus",
                "container_name": "prometheus",
                "image": "prom/prometheus",
                "depends_on": self.broker_containers + self.schema_registry_containers,
                "ports": {
                    9090: 9090
                },
                "volumes": [
                    "$PWD/volumes/prometheus.yml:/etc/prometheus/prometheus.yml"
                ]
            }
            proms.append(prometheus)

        return proms

    def generate_grafana_service(self):
        grafanas = []
        if self.args.prometheus:
            grafana = {
                "name": "grafana",
                "hostname": "grafana",
                "container_name": "grafana",
                "image": "grafana/grafana",
                "depends_on": [
                    "prometheus"
                ],
                "ports": {
                    3000: 3000
                },
                "volumes": [
                    "$PWD/volumes/provisioning:/etc/grafana/provisioning",
                    "$PWD/volumes/dashboards:/var/lib/grafana/dashboards"
                ]
            }
            grafanas.append(grafana)

        return grafanas

    @staticmethod
    def next_rack(rack, total_racks):
        rack = rack + 1
        if rack >= total_racks:
            rack = 0
        return rack


def load_configfile(arguments, configfile):
    config_parser = configparser.ConfigParser()
    with open(configfile) as f:
        # adding [top] section since ConfigParser needs sections, but don't want them in properties file
        lines = '[top]\n' + f.read()
        config_parser.read_string(lines)

    for k, v in config_parser.items('top'):
        # this is a hack
        # need to store values as int, not string, so we look at the original default's type
        # and cast accordingly

        if type(arguments.__getattribute__(k)) == int:
            arguments.__setattr__(k, int(v))
        else:
            arguments.__setattr__(k, v)

    return arguments


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Kafka docker-compose Generator")

    # optional with defaults

    parser.add_argument('-r', '--release', default=DEFAULT_RELEASE, help=f"Docker images release [{DEFAULT_RELEASE}]")

    parser.add_argument('-b', '--brokers', default=1, type=int, help="Number of Brokers [1]")
    parser.add_argument('-z', '--zookeepers', default=0, type=int,
                        help="Number of ZooKeepers [0]  - mutually exclusive with controllers")
    parser.add_argument('-c', '--controllers', default=0, type=int,
                        help="Number of Kafka Connector instances [0] - mutually exclusive with zookeepers")
    parser.add_argument('-s', '--schema-registries', default=0, type=int,
                        help="Number of Schema Registry instances [0]")
    parser.add_argument('-C', '--connect-instances', default=0, type=int,
                        help="Number of Kafka Connect instances [0]")
    parser.add_argument('--control-center', default=False, action='store_true',
                        help="Include Confluent Control Center [False]")

    parser.add_argument('--uuid', type=str, default=RANDOM_UUID,
                        help=f"UUID of the cluster [{RANDOM_UUID}]")

    parser.add_argument('-p', '--prometheus', default=False, action='store_true', help="Include Prometheus [False]")

    parser.add_argument('--kafka-container', default=KAFKA_CONTAINER,
                        help=f"Container used for Kafka, default [{KAFKA_CONTAINER}]")

    parser.add_argument('--racks', type=int, default=1,
                        help="Number of racks among which the brokers will be distributed evenly [1]")
    parser.add_argument('--zookeeper-groups', type=int, default=1,
                        help="Number of zookeeper groups in a hierarchy [1]")

    parser.add_argument('--docker-compose-file', default=DOCKER_COMPOSE_FILE,
                        help=f"Output file for docker-compose, default [{DOCKER_COMPOSE_FILE}]")

    parser.add_argument('--config',
                        help="Properties config file, values will be overriden by command line arguments")
    args = parser.parse_args()

    if args.config:
        args = load_configfile(args, args.config)

    # Check for inconsistencies
    if args.zookeepers and args.controllers:
        print("Zookeeper and Kafka Controllers (KRaft) are mutually exclusive", file=sys.stderr)
        sys.exit(2)

    generator = DockerComposeGenerator(args)
    generator.generate()

    print("Generated {}".format(args.docker_compose_file))
