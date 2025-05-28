import argparse
import sys

import configparser

from jinja2 import Environment, PackageLoader, select_autoescape

from generators.broker_generator import BrokerGenerator
from generators.connect_generator import ConnectGenerator
from generators.controller_generator import ControllerGenerator
from generators.schema_registry_generator import SchemaRegistryGenerator
from generators.zookeeper_generator import ZooKeeperGenerator

# constants

RANDOM_UUID = "Nk018hRAQFytWskYqtQduw"

DEFAULT_RELEASE = "7.9.1"
CONFLUENT_REPOSITORY = "confluentinc"
CONFLUENT_CONTAINER = "cp-server"
CONFLUENT_KAFKA_CLUSTER_CMD = "/usr/bin/kafka-cluster"

APACHE_REPOSITORY = "apache"
APACHE_CONTAINER = "kafka"
OSK_KAFKA_CLUSTER_CMD = "/opt/kafka/bin/kafka-cluster.sh"


LOCALBUILD = "localbuild"
JMX_PROMETHEUS_JAVA_AGENT_VERSION = "1.1.0"
JMX_PORT = "8091"
JMX_JAR_FILE = f"jmx_prometheus_javaagent-{JMX_PROMETHEUS_JAVA_AGENT_VERSION}.jar"
JMX_PROMETHEUS_JAVA_AGENT = f"-javaagent:/tmp/{JMX_JAR_FILE}={JMX_PORT}:/tmp/"
JMX_EXTERNAL_PORT = 10000
JMX_AGENT_PORT = 10100
HTTP_PORT = 10200

BROKER_EXTERNAL_BASE_PORT = 9090
BROKER_INTERNAL_BASE_PORT = 19090

LOCAL_VOLUMES = "$PWD/volumes/"

DOCKER_COMPOSE_FILE = "docker-compose.yml"

ZOOKEEPER_JMX_CONFIG = "zookeeper_config.yml"
ZOOKEEPER_PORT = "2181"

BROKER_JMX_CONFIG = "kafka_config.yml"
CONTROLLER_JMX_CONFIG = "kafka_controller.yml"
SCHEMA_REGISTRY_JMX_CONFIG = "schema-registry.yml"
CONNECT_JMX_CONFIG = "kafka_connect.yml"


class Generator:
    def __init__(self, base):
        self.base = base

    def generate(self):
        pass


class DockerComposeGenerator:
    def __init__(self, arguments):
        self.args = arguments

        self.env = Environment(
            loader=PackageLoader("docker-generator"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )

        if self.args.with_tc:
            self.repository = LOCALBUILD
            self.tc = "-tc"
        else:
            self.repository = self.args.repository
            self.tc = ""

        self.zookeepers = ""
        self.quorum_voters = ""
        self.bootstrap_servers = ""
        self.schema_registries = ""
        self.schema_registry_urls = ""
        self.connect_urls = ""
        self.ksqldb_urls = ""

        self.healthcheck_command = "KAFKA_OPTS= " + (OSK_KAFKA_CLUSTER_CMD if self.args.osk else CONFLUENT_KAFKA_CLUSTER_CMD)

        self.controllers = []

        self.controller_containers = []
        self.zookeeper_containers = []
        self.broker_containers = []
        self.connect_containers = []
        self.schema_registry_containers = []
        self.ksqldb_containers = []

        self.prometheus_jobs = []

        self.jmx_external_port_counter = JMX_EXTERNAL_PORT
        self.agent_port_counter = JMX_AGENT_PORT
        self.http_port_counter = HTTP_PORT

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

    def next_http_port(self):
        self.http_port_counter += 1
        return self.http_port_counter

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
        if self.args.shared_mode:
            return min(3, self.args.brokers + self.args.controllers)
        else:
            return min(3, self.args.brokers)

    def min_insync_replicas(self):
        return max(1, self.replication_factor() - 1)

    def generate_services(self):
        services = []
        zookeeper_generator = ZooKeeperGenerator(self)
        controller_generator = ControllerGenerator(self)
        broker_generator = BrokerGenerator(self)
        schema_registry_generator = SchemaRegistryGenerator(self)
        connect_generator = ConnectGenerator(self)

        services += zookeeper_generator.generate()
        services += controller_generator.generate()
        services += broker_generator.generate()
        services += schema_registry_generator.generate()
        services += connect_generator.generate()

        services += self.generate_ksqldb_services()
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

    def generate_depends_on(self):
        if self.args.shared_mode:
            return self.controller_containers + self.broker_containers + self.schema_registry_containers
        else:
            return self.broker_containers + self.schema_registry_containers

    def generate_ksqldb_services(self):
        ksqldbs = []
        targets = []
        ksqldb_hosts = []

        job = {
            "name": "ksqldb",
            "scrape_interval": "5s",
            "targets": targets
        }

        for ksqldb_id in range(1, self.args.ksqldb_instances + 1):
            port = 8087 + ksqldb_id

            name = self.create_name("ksqldb", ksqldb_id)

            ksqldb = {
                'name': name,
                "hostname": name,
                "container_name": name,
                "image": f"{self.repository}/cp-ksqldb-server{self.tc}:" + self.args.release,
                "depends_on_condition": self.generate_depends_on(),
                "environment": {
                    "KSQL_LISTENERS": f"http://0.0.0.0:{port}",
                    "KSQL_BOOTSTRAP_SERVERS": self.bootstrap_servers,
                    "KSQL_KSQL_LOGGING_PROCESSING_STREAM_AUTO_CREATE": "true",
                    "KSQL_KSQL_LOGGING_PROCESSING_TOPIC_AUTO_CREATE": "true",
                    "KSQL_KSQL_CONNECT_URL": self.connect_urls,
                    "KSQL_KSQL_SCHEMA_REGISTRY_URL": self.schema_registry_urls,
                    "KSQL_KSQL_SERVICE_ID": "kafka-docker-composer",
                    "KSQL_KSQL_HIDDEN_TOPICS": "^_.*",
                    "KSQL_KSQL_INTERNAL_TOPICS_REPLICAS": self.replication_factor(),
                    "KSQL_KSQL_LOGGING_PROCESSING_TOPIC_REPLICATION_FACTOR": self.replication_factor(),
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
            self.ksqldb_containers.append(name)

        self.ksqldb_urls = ",".join(ksqldb_hosts)

        return ksqldbs

    def generate_control_center_service(self):
        control_centers = []

        if self.args.control_center:
            control_center = {
                "name": "control-center",
                "hostname": "control-center",
                "container_name": "control-center",
                "image": f"{self.repository}/cp-enterprise-control-center{self.tc}:" + self.args.release,
                "depends_on_condition": self.generate_depends_on() + self.connect_containers + self.ksqldb_containers,
                "environment": {
                    "CONTROL_CENTER_BOOTSTRAP_SERVERS": self.bootstrap_servers,
                    "CONTROL_CENTER_SCHEMA_REGISTRY_URL": self.schema_registry_urls,
                    "CONTROL_CENTER_REPLICATION_FACTOR": self.replication_factor(),
                    "CONTROL_CENTER_CONNECT_CONNECT_CLUSTER": self.connect_urls,
                    "CONTROL_CENTER_KSQL_KSQL_URL": self.ksqldb_urls
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

    def generate_prometheus_service(self):
        proms = []
        if self.args.prometheus:
            prometheus = {
                "name": "prometheus",
                "hostname": "prometheus",
                "container_name": "prometheus",
                "image": "prom/prometheus",
                "depends_on_condition": self.broker_containers + self.schema_registry_containers,
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
                    "$PWD/volumes/dashboards:/var/lib/grafana/dashboards",
                    "$PWD/volumes/config.ini:/etc/grafana/config.ini"
                ],
                "environment": {
                    "GF_PATHS_CONFIG": "/etc/grafana/config.ini"
                }
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
    parser.add_argument('--repository', default=CONFLUENT_REPOSITORY, help=f"Repository for the docker image [{CONFLUENT_REPOSITORY}]")
    parser.add_argument('--kafka-container', default=CONFLUENT_CONTAINER,
                        help=f"Container used for Kafka [{CONFLUENT_CONTAINER}]")

    parser.add_argument('--osk', action="store_true",help="Use Open Source Apache Kafka")

    parser.add_argument('--with-tc', action="store_true", help="Build and use a local image with tc enabled")
    parser.add_argument("--shared-mode", action="store_true", help="Enable shared mode for controllers")

    parser.add_argument('-b', '--brokers', default=1, type=int, help="Number of Brokers [1]")
    parser.add_argument('-z', '--zookeepers', default=0, type=int,
                        help="Number of ZooKeepers [0]  - mutually exclusive with controllers")
    parser.add_argument('-c', '--controllers', default=0, type=int,
                        help="Number of Kafka controller instances [0] - mutually exclusive with ZooKeepers")
    parser.add_argument('-s', '--schema-registries', default=0, type=int,
                        help="Number of Schema Registry instances [0]")
    parser.add_argument('-C', '--connect-instances', default=0, type=int,
                        help="Number of Kafka Connect instances [0]")
    parser.add_argument('-k', '--ksqldb-instances', default=0, type=int,
                        help="Number of ksqlDB instances [0]")
    parser.add_argument('--control-center', default=False, action='store_true',
                        help="Include Confluent Control Center [False]")

    parser.add_argument('--uuid', type=str, default=RANDOM_UUID,
                        help=f"UUID of the cluster [{RANDOM_UUID}]")

    parser.add_argument('-p', '--prometheus', default=False, action='store_true', help="Include Prometheus [False]")

    parser.add_argument('--racks', type=int, default=1,
                        help="Number of racks among which the brokers will be distributed evenly [1]")
    parser.add_argument('--zookeeper-groups', type=int, default=1,
                        help="Number of zookeeper groups in a hierarchy [1]")

    parser.add_argument('--docker-compose-file', default=DOCKER_COMPOSE_FILE,
                        help=f"Output file for docker-compose, default [{DOCKER_COMPOSE_FILE}]")

    parser.add_argument('--config',
                        help="Properties config file, values will be overridden by command line arguments")
    args = parser.parse_args()

    if args.osk:
        args.repository = APACHE_REPOSITORY
        args.kafka_container = APACHE_CONTAINER
        args.release = "latest"

    if args.config:
        args = load_configfile(args, args.config)

    # Check for inconsistencies
    if args.zookeepers and args.controllers:
        print("Zookeeper and Kafka Controllers (KRaft) are mutually exclusive", file=sys.stderr)
        sys.exit(2)

    if args.zookeepers and args.shared_mode:
        print("Zookeeper cannot run in shared mode with a Broker. Nice try!", file=sys.stderr)
        sys.exit(2)

    generator = DockerComposeGenerator(args)
    generator.generate()

    print("Generated {}".format(args.docker_compose_file))
