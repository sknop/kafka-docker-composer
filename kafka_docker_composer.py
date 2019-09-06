from __future__ import print_function

import argparse
import re
import os.path
import sys

import configparser

# constants

DEFAULT_RELEASE="5.3.0"

TEMPLATES_DIR = "templates"
BROKER_TEMPLATE = os.path.join(TEMPLATES_DIR, "kafka.template")
ZOOKEEPER_TEMPLATE = os.path.join(TEMPLATES_DIR, "zookeeper.template")
SCHEMA_REGISTRY_TEMPLATE = os.path.join(TEMPLATES_DIR, "schema-registry.template")
PROMETHEUS_TEMPLATE = os.path.join(TEMPLATES_DIR, "prometheus.template")
PROMETHEUS_CONFIG_TEMPLATE = os.path.join(TEMPLATES_DIR, "prometheus.yml.template")
PROMETHEUS_CONFIG = os.path.join("volumes","prometheus.yml")  # TODO make configurable?
CONTROL_CENTER_TEMPLATE = os.path.join(TEMPLATES_DIR, "control-center.template")
DOCKER_COMPOSE_TEMPLATE = os.path.join(TEMPLATES_DIR, "docker-compose.template")
DOCKER_COMPOSE_FILE = "docker-compose.yaml"

# known variables to fill
# common

RELEASE = "{{release}}"

# single (broker)
#
BROKER_NAME = "{{broker-name}}"
BROKER_ID = "{{broker-id}}"
BROKER_PORT = "{{broker-port}}"
BROKER_PORT_INTERNAL = "{{broker-port-internal}}"
BROKER_PORT_EXTERNAL = "{{broker-port-external}}"
BROKER_ADVERTISED_PORT_EXTERNAL = "{{broker-advertised-port-external}}"
BROKER_ADVERTISED_PORT_INTERNAL = "{{broker-advertised-port-internal}}"
BROKER_JMX_PORT = "{{broker-jmx-port}}"
BROKER_RACK = "{{broker-rack}}"

BROKER_INTERNAL_PROTOCOL = "{{broker-internal-protocol}}"
BROKER_EXTERNAL_PROTOCOL = "{{broker-external-protocol}}"

#
# single (zookeeper)
#
ZOOKEEPER_NAME = "{{zookeeper-name}}"
ZOOKEEPER_ID = "{{zookeeper-id}}"
ZOOKEEPER_PORT = "{{zookeeper-port}}"
ZOOKEEPER_JMX_PORT = "{{zookeeper-jmx-port}}"
ZOOKEEPER_GROUPS = "{{zookeeper-groups}}"

#
# single (schema registry)
#
SCHEMA_REGISTRY_NAME = "{{schema-registry-name}}"
SCHEMA_REGISTRY_PORT = "{{schema-registry-port}}"
PREVIOUS_SCHEMA_REGISTRY_CONTAINERS = "{{previous-schema-registry-containers}}"

# single (prometheus)

JMX_BROKER_PORTS = "{{jmx-broker-ports}}"
JMX_ZOOKEEPER_PORTS = "{{jmx-zookeeper-ports}}"

#
# services
#
ZOOKEEPER_SERVICES = "{{zookeeper-services}}"
BROKER_SERVICES = "{{broker-services}}"
SCHEMA_REGISTRY_SERVICES = "{{schema-registry-services}}"
PROMETHEUS_SERVICE = "{{prometheus-service}}"
CONTROL_CENTER_SERVICE = "{{control-center-service}}"

#
# multiple
#
ZOOKEEPER_CONTAINERS = "{{zookeeper-containers}}"  # array of dependencies
BROKER_CONTAINERS = "{{broker-containers}}"  # array of dependencies
SCHEMA_CONTAINERS = "{{schema-registry-containers}}" # array of dependencies (for control center)
ZOOKEEPER_PORTS = "{{zookeeper-ports}}"  # host:port[,host:port]*
ZOOKEEPER_INTERNAL_PORTS = "{{zookeeper-internal-ports}}"  # host:2888:3888[;host:2888:3888]*
KAFKA_BOOTSTRAP_SERVERS = "{{kafka-bootstrap-servers}}"


class OffsetNotFoundException(Exception):
    def __init__(self, desc):
        super(OffsetNotFoundException, self).__init__(desc)


class YamlGenerator:
    def __init__(self, args):
        self.args = args

        with open(self.args.docker_compose_template) as f:
            self.master_template = f.read()

        with open(self.args.broker_template) as f:
            self.broker_template = f.read()

        with open(self.args.zookeeper_template) as f:
            self.zookeeper_template = f.read()

        with open(self.args.schema_registry_template) as f:
            self.schema_registry_template = f.read()

        if args.prometheus:
            with open(self.args.prometheus_template) as f:
                self.prometheus_template = f.read()

            with open(self.args.prometheus_config_template) as f:
                self.prometheus_config_template = f.read()

            try:
                self.config_offset = YamlGenerator.find_offset(self.prometheus_config_template, JMX_BROKER_PORTS)
            except OffsetNotFoundException:
                self.config_offset = ""

        self.zookeeper_offset = YamlGenerator.find_offset(self.master_template, ZOOKEEPER_SERVICES)
        self.broker_offset = YamlGenerator.find_offset(self.master_template, BROKER_SERVICES)
        self.depends_offset = YamlGenerator.find_offset(self.broker_template, ZOOKEEPER_CONTAINERS)

        try:  # might not exist, need to catch Exception
            self.schema_registry_offset = YamlGenerator.find_offset(self.master_template, SCHEMA_REGISTRY_SERVICES)
        except OffsetNotFoundException:
            self.schema_registry_offset = ""

        try:  # might not exist, need to catch Exception
            self.prometheus_offset = YamlGenerator.find_offset(self.master_template, PROMETHEUS_SERVICE)
        except OffsetNotFoundException:
            self.prometheus_offset = ""

        if args.control_center:
            with open(self.args.control_center_template) as f:
                self.control_center_template = f.read()

        try:  # might not exist, need to catch Exception
            self.control_center_offset = YamlGenerator.find_offset(self.master_template, CONTROL_CENTER_SERVICE)
        except OffsetNotFoundException:
            self.control_center_offset = ""

        self.zookeeper_containers = ""
        self.zookeeper_ports = ""
        self.zookeeper_internal_ports = ""
        self.zookeeper_groups = ""

        self.bootstrap_servers = ""
        self.broker_containers = ""
        self.schema_registry_containers = ""

        self.brokers = []
        self.zookeepers = []

    def generate(self):
        zookeeper_services = self.generate_zookeeper_services()
        broker_services = self.generate_broker_services()
        schema_registry_services = self.generate_schema_registry_service()
        prometheus_service = self.generate_prometheus_service()
        control_center_service = self.generate_control_center_service()

        if self.args.prometheus:
            self.generate_prometheus_config()

        zookeeper_placeholder = self.zookeeper_offset + ZOOKEEPER_SERVICES
        broker_placeholder = self.broker_offset + BROKER_SERVICES
        schema_registry_placeholder = self.schema_registry_offset + SCHEMA_REGISTRY_SERVICES
        prometheus_placeholder = self.prometheus_offset + PROMETHEUS_SERVICE
        control_center_placeholder = self.control_center_offset + CONTROL_CENTER_SERVICE

        output_file = self.master_template
        output_file = output_file.replace(zookeeper_placeholder, zookeeper_services)
        output_file = output_file.replace(broker_placeholder, broker_services)
        output_file = output_file.replace(schema_registry_placeholder, schema_registry_services)
        output_file = output_file.replace(prometheus_placeholder, prometheus_service)
        output_file = output_file.replace(control_center_placeholder, control_center_service)

        with open(self.args.docker_compose_file, "w") as yaml_file:
            yaml_file.write(output_file)

    def generate_zookeeper_services(self):
        if self.args.zookeeper_groups > 1:
            zookeeper_group = ""

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

            self.zookeeper_groups = ";".join(groups)

        for zk in range(1, self.args.zookeepers + 1):
            zookeeper = {}
            zookeeper[RELEASE] = self.args.release
            zookeeper[ZOOKEEPER_NAME] = "zookeeper" + str(zk)
            zookeeper[ZOOKEEPER_ID] = str(zk)
            zookeeper[ZOOKEEPER_PORT] = "2181"
            zookeeper[ZOOKEEPER_JMX_PORT] = "9999"
            zookeeper[ZOOKEEPER_GROUPS] = self.zookeeper_groups

            self.zookeepers.append(zookeeper)

        self.zookeeper_containers = "\n{}".format(self.depends_offset). \
            join(['- ' + x[ZOOKEEPER_NAME] for x in self.zookeepers])
        self.zookeeper_ports = ",".join([x[ZOOKEEPER_NAME] + ':' + x[ZOOKEEPER_PORT] for x in self.zookeepers])
        self.zookeeper_internal_ports = ";".join([x[ZOOKEEPER_NAME] + ":2888:3888" for x in self.zookeepers])

        for zk in self.zookeepers:
            zk[ZOOKEEPER_INTERNAL_PORTS] = self.zookeeper_internal_ports

        services = "\n".join([self.generate_one_zookeeper_service(x) for x in self.zookeepers])

        return services

    def generate_one_zookeeper_service(self, zookeeper):
        service = self.zookeeper_template
        for key, value in zookeeper.items():
            service = service.replace(key, value)

        lines = service.split('\n')
        result = [self.zookeeper_offset + line for line in lines]

        return "\n".join(result)

    def generate_broker_services(self):
        rack = 0

        for id in range(1, self.args.brokers + 1):
            port = 9090 + id
            internal_port = 19090 + id

            broker = {}
            broker[RELEASE] = self.args.release
            broker[BROKER_NAME] = "kafka" + str(id)
            broker[BROKER_ID] = str(id)
            broker[BROKER_PORT] = str(port)
            broker[BROKER_PORT_INTERNAL] = "{}:{}".format(broker[BROKER_NAME], str(internal_port))
            broker[BROKER_PORT_EXTERNAL] = "{}:{}".format(broker[BROKER_NAME], str(port))
            broker[BROKER_ADVERTISED_PORT_INTERNAL] = "{}:{}".format(broker[BROKER_NAME], str(internal_port))
            broker[BROKER_ADVERTISED_PORT_EXTERNAL] = "{}:{}".format("localhost", str(port))
            broker[BROKER_JMX_PORT] = "9999"
            broker[ZOOKEEPER_CONTAINERS] = self.zookeeper_containers
            broker[ZOOKEEPER_PORTS] = self.zookeeper_ports
            broker[BROKER_RACK] = str(rack)
            broker[BROKER_INTERNAL_PROTOCOL] = self.args.broker_internal_protocol
            broker[BROKER_EXTERNAL_PROTOCOL] = self.args.broker_external_protocol

            self.brokers.append(broker)

            rack = YamlGenerator.next_rack(rack, self.args.racks)

        self.broker_containers = "\n{}".format(self.depends_offset). \
            join(['- ' + x[BROKER_NAME] for x in self.brokers])

        services = "\n".join([self.generate_one_broker_service(x) for x in self.brokers])

        self.bootstrap_servers = ",".join(["PLAINTEXT://" + x[BROKER_PORT_INTERNAL] for x in self.brokers])

        return services

    def generate_one_broker_service(self, broker):
        service = self.broker_template
        for key, value in broker.items():
            service = service.replace(key, value)

        lines = service.split('\n')
        result = [self.broker_offset + line for line in lines]

        return "\n".join(result)

    def generate_schema_registry_service(self):
        schema_registries = []

        for id in range(1, self.args.schema_registries + 1):
            port = 8080 + id

            # Collect all previous schema-registry entries to set up a hierarchy
            previous_containers = "\n{}".format(self.depends_offset). \
                join(['- ' + x[SCHEMA_REGISTRY_NAME] for x in schema_registries])

            schema_registry = {
                                RELEASE: self.args.release,
                                SCHEMA_REGISTRY_NAME: "schema-registry" + str(id),
                                KAFKA_BOOTSTRAP_SERVERS: self.bootstrap_servers,
                                BROKER_CONTAINERS: self.broker_containers,
                                SCHEMA_REGISTRY_PORT: str(port),
                                PREVIOUS_SCHEMA_REGISTRY_CONTAINERS: previous_containers
                               }

            schema_registries.append(schema_registry)

        self.schema_registry_containers = "\n{}".format(self.depends_offset). \
            join(['- ' + x[SCHEMA_REGISTRY_NAME] for x in schema_registries])

        services = "\n".join([self.generate_one_schema_registry_service(x) for x in schema_registries])

        return services

    def generate_one_schema_registry_service(self, schema):
        service = self.schema_registry_template
        for key, value in schema.items():
            service = service.replace(key, value)

        lines = service.split('\n')
        result = [self.schema_registry_offset + line for line in lines]

        return "\n".join(result)

    def generate_control_center_service(self):
        if self.args.control_center:
            service = self.control_center_template

            control_center = {
                RELEASE: self.args.release,
                ZOOKEEPER_CONTAINERS: self.zookeeper_containers,
                BROKER_CONTAINERS: self.broker_containers,
                SCHEMA_CONTAINERS: self.schema_registry_containers,
                KAFKA_BOOTSTRAP_SERVERS: ",".join([x[BROKER_PORT_INTERNAL] for x in self.brokers]),
                ZOOKEEPER_PORTS: self.zookeeper_ports
            }

            for key,value in control_center.items():
                service = service.replace(key, value)

            lines = service.split('\n')
            result = '\n'.join([self.control_center_offset + line for line in lines])

            return result
        else:
            return ""

    def generate_prometheus_service(self):
        if self.args.prometheus:
            prometheus = {BROKER_CONTAINERS: self.broker_containers}

            service = self.prometheus_template
            for key, value in prometheus.items():
                service = service.replace(key, value)

            lines = service.split('\n')
            result = "\n".join([self.prometheus_offset + line for line in lines])

            return result
        else:
            return ""

    def generate_prometheus_config(self):
        config = self.prometheus_config_template
        jmx_broker_ports = '\n{}'.format(self.config_offset).\
            join(["- {}:8080".format(x[BROKER_NAME]) for x in self.brokers])
        jmx_zookeeper_ports = '\n{}'.format(self.config_offset).\
            join(["- {}:8080".format(x[ZOOKEEPER_NAME]) for x in self.zookeepers])

        config = config.replace(JMX_ZOOKEEPER_PORTS, jmx_zookeeper_ports)
        config = config.replace(JMX_BROKER_PORTS, jmx_broker_ports)

        with open(PROMETHEUS_CONFIG, 'w') as f:
            f.write(config)

    @staticmethod
    def next_rack(rack, total_racks):
        rack = rack + 1
        if rack >= total_racks:
            rack = 0
        return rack

    @staticmethod
    def find_offset(template, placeholder):
        lines = template.split("\n")
        pattern = re.compile(r"^(\s*){}".format(placeholder))
        for line in lines:
            match = pattern.match(line)
            if match:
                return match.group(1)
        raise OffsetNotFoundException("Offset for placeholder {} not found".format(placeholder))


def load_configfile(args, configfile):
    parser = configparser.ConfigParser()
    with open(configfile) as f:
        # adding [top] section since ConfigParser needs sections, but don't want them in properties file
        lines = '[top]\n' + f.read()
        parser.read_string(lines)

    for k, v in parser.items('top'):
        # this is a hack
        # need to store values as int, not string, so we look at the original default's type
        # and cast accordingly

        if type(args.__getattribute__(k)) == int:
            args.__setattr__(k, int(v))
        else:
            args.__setattr__(k, v)

    return args


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Kafka docker-compose Generator")

    # optional with defaults

    parser.add_argument('-r', '--release', default=DEFAULT_RELEASE, help="Docker images release")

    parser.add_argument('-b', '--brokers', default=1, type=int, help="Number of Brokers [1]")
    parser.add_argument('-z', '--zookeepers', default=1, type=int, help="Number of ZooKeepers [1]")
    parser.add_argument('-s', '--schema-registries', default=0, type=int,
                        help="Number of Schema Registry instances [0]")
    parser.add_argument('-p', '--prometheus', default=False, action='store_true', help="Include Prometheus [False]")
    parser.add_argument('--control-center', default=False, action='store_true', help="Include Confluent Control Center [False]")

    parser.add_argument('--docker-compose-template', default=DOCKER_COMPOSE_TEMPLATE,
                        help="Template file for docker-compose, default \"{}\"".format(DOCKER_COMPOSE_TEMPLATE))
    parser.add_argument('--broker-template', default=BROKER_TEMPLATE,
                        help="Template file for brokers, default \"{}\"".format(BROKER_TEMPLATE))
    parser.add_argument('--zookeeper-template', default=ZOOKEEPER_TEMPLATE,
                        help="Template file for zookeepers, default \"{}\"".format(ZOOKEEPER_TEMPLATE))
    parser.add_argument('--schema-registry-template', default=SCHEMA_REGISTRY_TEMPLATE,
                        help="Template file for schema registry, default \"{}\"".format(SCHEMA_REGISTRY_TEMPLATE))
    parser.add_argument('--control-center-template', default=CONTROL_CENTER_TEMPLATE,
                        help="Template file for control center, default \"{}\"".format(CONTROL_CENTER_TEMPLATE))
    parser.add_argument('--prometheus-template', default=PROMETHEUS_TEMPLATE,
                        help="Template file for prometheus, default \"{}\"".format(PROMETHEUS_TEMPLATE))
    parser.add_argument('--prometheus-config-template', default=PROMETHEUS_CONFIG_TEMPLATE,
                        help="Template file for prometheus config, default \"{}\"".format(PROMETHEUS_CONFIG_TEMPLATE))
    parser.add_argument('--docker-compose-file', default=DOCKER_COMPOSE_FILE,
                        help="Output file for docker-compose, default \"{}\"".format(DOCKER_COMPOSE_FILE))

    parser.add_argument('--broker-internal-protocol', default="PLAINTEXT",
                        help="Internal protocol used (default PLAINTEXT)")
    parser.add_argument('--broker-external-protocol', default="PLAINTEXT",
                        help="External protocol used (default PLAINTEXT)")

    parser.add_argument('--racks', type=int, default=1,
                        help="Number of racks among which the brokers will be distributed evenly")
    parser.add_argument('--zookeeper-groups', type=int, default=1,
                        help="Number of zookeeper groups in a hierarchy")

    parser.add_argument('-c', '--config',
                        help="Properties config file, values will be overriden by command line arguments")
    args = parser.parse_args()

    if args.config:
        args = load_configfile(args, args.config)

    generator = YamlGenerator(args)
    generator.generate()

    print("Generated {}".format(args.docker_compose_file))
