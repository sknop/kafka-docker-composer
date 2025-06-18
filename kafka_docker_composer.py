import argparse
import sys

import configparser

from jinja2 import Environment, PackageLoader, select_autoescape

from constants import CONTROL_CENTER_NEXT_GEN_RELEASE
from generators.broker_generator import BrokerGenerator
from generators.connect_generator import ConnectGenerator
from generators.control_center_generator import ControlCenterGenerator
from generators.control_center_next_gen_generator import ControlCenterNextGenerationGenerator
from generators.controller_generator import ControllerGenerator
from generators.ksqldb_generator import KSQLDBGenerator
from generators.schema_registry_generator import SchemaRegistryGenerator
from generators.zookeeper_generator import ZooKeeperGenerator

from constants import *

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
        ksqldb_generator = KSQLDBGenerator(self)
        control_center_generator = ControlCenterGenerator(self)
        control_center_next_gen_generator = ControlCenterNextGenerationGenerator(self)

        services += zookeeper_generator.generate()
        services += controller_generator.generate()
        services += broker_generator.generate()
        services += schema_registry_generator.generate()
        services += connect_generator.generate()
        services += ksqldb_generator.generate()
        services += control_center_generator.generate()
        services += control_center_next_gen_generator.generate()

        services += self.generate_prometheus_service()
        services += self.generate_grafana_service()
        services += self.generate_alertmanager_service()

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

    def generate_prometheus_service(self):
        proms = []
        if self.args.prometheus:
            prometheus = {
                "name": "prometheus",
                "hostname": "prometheus",
                "container_name": "prometheus",
                "image": "confluentinc/cp-enterprise-prometheus:" + self.args.control_center_next_gen_release,
                "depends_on_condition": self.broker_containers + self.schema_registry_containers,
                "ports": {
                    9090: 9090
                },
                "volumes": [
                    "$PWD/volumes/prometheus.yml:/etc/prometheus/prometheus.yml",
                    "$PWD/volumes/"
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

    def generate_alertmanager_service(self):
        alertmanagers = []
        if self.args.control_center_next_gen:
            alertmanager = {
                "name": "alertmanager",
                "hostname": "cp-enterprise-alertmanager",
                "container_name": "alertmanager",
                "image": f"{self.args.repository}/cp-enterprise-alertmanager:" + self.args.control_center_next_gen_release,
                "depends_on": [
                    "prometheus"
                ],
                "ports" : {
                    29093 : 9093
                },
                "volumes": {
                    LOCAL_VOLUMES + "config:/mnt/config"
                }
            }
            alertmanagers.append(alertmanager)

        return alertmanagers

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
    parser.add_argument('--control-center-next-gen', default=False, action='store_true',
                        help="Add net-gen Confluent Control Center [False]")
    parser.add_argument('--control-center-next-gen-release', default=CONTROL_CENTER_NEXT_GEN_RELEASE,
                        help=f"Next generation release [{CONTROL_CENTER_NEXT_GEN_RELEASE}]")

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

    if args.control_center and args.control_center_next_gen:
        print("Choose either old or new type of the Control Center, not both!", file=sys.stderr)
        sys.exit(2)

    generator = DockerComposeGenerator(args)
    generator.generate()

    print("Generated {}".format(args.docker_compose_file))
