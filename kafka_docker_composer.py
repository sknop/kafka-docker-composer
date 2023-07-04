import argparse
import sys

import configparser

from jinja2 import Environment, PackageLoader, select_autoescape

# constants

DEFAULT_RELEASE = "7.4.0"
JMX_PROMETHEUS_JAVA_AGENT_VERSION = "0.18.0"
JMX_JAR_FILE = "jmx_prometheus_javaagent-" + JMX_PROMETHEUS_JAVA_AGENT_VERSION + ".jar"
JMX_PROMETHEUS_JAVA_AGENT = "-javaagent:/tmp/" + JMX_JAR_FILE + "=8091:/tmp/"

LOCAL_VOLUMES = "$PWD/volumes/"

DOCKER_COMPOSE_FILE = "docker-compose.yaml"
KAFKA_CONTAINER = "cp-server"

ZOOKEEPER_JMX_CONFIG = "zookeeper_config.yml"
ZOOKEEPER_PORT = "2181"

BROKER_JMX_CONFIG = "kafka_config.yml"


class YamlGenerator:
    def __init__(self, arguments):
        self.args = arguments

        env = Environment(
            loader=PackageLoader("docker-generator"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )

        self.template = env.get_template('docker-compose.j2')

        self.zookeepers = ""
        self.controllers = ""
        self.bootstrap_servers = ""
        self.schema_registries = ""

        self.controller_containers = []
        self.zookeeper_containers = []
        self.broker_containers = []
        self.schema_registry_containers = []

    def generate(self):
        services = []

        services += self.generate_zookeeper_services()
        services += self.generate_controller_services()
        services += self.generate_broker_services()
        services += self.generate_schema_registry_service()
        services += self.generate_control_center_service()
        services += self.generate_prometheus_service()
        services += self.generate_grafana_service()

        variables = {
            "docker_compose_version": "3.8",
            "services": services
        }
        result = self.template.render(variables)

        with open(self.args.docker_compose_file, "w") as yaml_file:
            yaml_file.write(result)

    def generate_controller_services(self):
        controllers = []

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

        for zk in range(1, self.args.zookeepers + 1):
            zookeeper_external_port = 2180 + zk

            zookeeper = {}

            name = "zookeeper" + str(zk)
            zookeeper["name"] = name
            zookeeper["hostname"] = name
            zookeeper["container_name"] = name

            zookeeper_servers.append(name + ":2888:3888")

            zookeeper["image"] = "confluentinc/cp-zookeeper:" + self.args.release

            environment = {
                "ZOOKEEPER_SERVER_ID": zk,
                "ZOOKEEPER_CLIENT_PORT": ZOOKEEPER_PORT,
                "ZOOKEEPER_TICK_TIME": 2000,
                "KAFKA_JMX_PORT": 9999,
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

            zookeeper["ports"] = {
                zookeeper_external_port: ZOOKEEPER_PORT
            }

            zookeepers.append(zookeeper)

        zk_servers = ";".join(zookeeper_servers)
        for zk in zookeepers:
            zk["environment"]["ZOOKEEPER_SERVERS"] = zk_servers

        self.zookeepers = ",".join([z["name"] + ":" + ZOOKEEPER_PORT for z in zookeepers])

        self.zookeeper_containers = [z["name"] for z in zookeepers]

        return zookeepers

    def generate_broker_services(self):
        rack = 0

        brokers = []
        bootstrap_servers = []

        for broker_id in range(1, self.args.brokers + 1):
            port = 9090 + broker_id
            internal_port = 19090 + broker_id

            broker = {}

            name = "kafka" + str(broker_id)
            broker["name"] = name
            broker["hostname"] = name
            broker["container_name"] = name

            broker["image"] = f"confluentinc/{KAFKA_CONTAINER}:" + self.args.release

            broker["depends_on"] = self.zookeeper_containers

            broker["environment"] = {
                "KAFKA_BROKER_ID": broker_id,
                "KAFKA_ZOOKEEPER_CONNECT": self.zookeepers,
                "KAFKA_LISTENERS": f"PLAINTEXT://{name}:{internal_port}, EXTERNAL://{name}:{port}",
                "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP": "PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT",
                "KAFKA_ADVERTISED_LISTENERS": f"PLAINTEXT://{name}:{internal_port}, EXTERNAL://localhost:{port}",
                "KAFKA_INTER_BROKER_LISTENER_NAME": "PLAINTEXT",
                "KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS": 0,
                "KAFKA_JMX_PORT": 9999,
                "KAFKA_JMX_HOSTNAME": name,
                "KAFKA_BROKER_RACK": f"rack-{rack}",
                "KAFKA_OPTS": JMX_PROMETHEUS_JAVA_AGENT + BROKER_JMX_CONFIG
            }

            broker["ports"] = {
                port: port
            }

            broker["volumes"] = [
                LOCAL_VOLUMES + JMX_JAR_FILE + ":/tmp/" + JMX_JAR_FILE,
                LOCAL_VOLUMES + BROKER_JMX_CONFIG + ":/tmp/" + BROKER_JMX_CONFIG
            ]

            brokers.append(broker)
            bootstrap_servers.append(f"{name}:{internal_port}")

            rack = YamlGenerator.next_rack(rack, self.args.racks)

        self.bootstrap_servers = ",".join(bootstrap_servers)
        self.broker_containers = [b["name"] for b in brokers]

        return brokers

    def generate_schema_registry_service(self):
        schema_registries = []

        schema_registry_hosts = []

        for schema_id in range(1, self.args.schema_registries + 1):
            port = 8090 + schema_id

            name = "schema-registry" + str(schema_id)

            schema_registry = {
                "name": name,
                "hostname": name,
                "container_name": name,
                "image": "confluentinc/cp-schema-registry:" + self.args.release,
                "depends_on": self.broker_containers,
                "environment": {
                    "SCHEMA_REGISTRY_HOST_NAME": name,
                    "SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS": self.bootstrap_servers,
                    "SCHEMA_REGISTRY_LISTENERS": f"http://0.0.0.0:{port}"
                },
                "port": {
                    port: port
                }}

            schema_registries.append(schema_registry)
            schema_registry_hosts.append(f"{name}:{port}")

        self.schema_registries = ",".join(schema_registry_hosts)
        self.schema_registry_containers = [s["name"] for s in schema_registries]

        return schema_registries

    def generate_control_center_service(self):
        control_centers = []

        if self.args.control_center:

            control_center = {
                "name": "control-center",
                "hostname": "control-center",
                "container_name": "control-center",
                "image": "confluentinc/cp-enterprise-control-center:" + self.args.release,
                "depends_on" : self.broker_containers + self.zookeeper_containers + self.schema_registry_containers,
                "environment": {
                    "CONTROL_CENTER_BOOTSTRAP_SERVERS": self.bootstrap_servers,
                    "CONTROL_CENTER_SCHEMA_REGISTRY_URL": self.schema_registries
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
                "depends_on": self.broker_containers,
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

    parser.add_argument('-r', '--release', default=DEFAULT_RELEASE, help="Docker images release")

    parser.add_argument('-b', '--brokers', default=1, type=int, help="Number of Brokers [1]")
    parser.add_argument('-z', '--zookeepers', default=0, type=int,
                        help="Number of ZooKeepers [0]  - mutually exclusive with controllers")
    parser.add_argument('-c', '--controllers', default=0, type=int,
                        help="Number of Kafka Connector instances [0] - mutually exclusive with zookeepers")
    parser.add_argument('-s', '--schema-registries', default=0, type=int,
                        help="Number of Schema Registry instances [0]")
    parser.add_argument('--control-center', default=False, action='store_true',
                        help="Include Confluent Control Center [False]")

    parser.add_argument('-p', '--prometheus', default=False, action='store_true', help="Include Prometheus [False]")

    parser.add_argument('--kafka-container', default=KAFKA_CONTAINER,
                        help="Container used for Kafka, default \"{}\"".format(KAFKA_CONTAINER))

    parser.add_argument('--broker-internal-protocol', default="PLAINTEXT",
                        help="Internal protocol used (default PLAINTEXT)")
    parser.add_argument('--broker-external-protocol', default="PLAINTEXT",
                        help="External protocol used (default PLAINTEXT)")

    parser.add_argument('--racks', type=int, default=1,
                        help="Number of racks among which the brokers will be distributed evenly")
    parser.add_argument('--zookeeper-groups', type=int, default=1,
                        help="Number of zookeeper groups in a hierarchy")

    parser.add_argument('--docker-compose-file', default=DOCKER_COMPOSE_FILE,
                        help="Output file for docker-compose, default \"{}\"".format(DOCKER_COMPOSE_FILE))

    parser.add_argument('--config',
                        help="Properties config file, values will be overriden by command line arguments")
    args = parser.parse_args()

    if args.config:
        args = load_configfile(args, args.config)

    # Check for inconsistencies
    if (args.zookeepers or args.zookeeper_groups) and args.controllers:
        print("Zookeeper and Kafka Controllers (KRaft) are mutually exclusive", file=sys.stderr)
        sys.exit(2)

    generator = YamlGenerator(args)
    generator.generate()

    print("Generated {}".format(args.docker_compose_file))
