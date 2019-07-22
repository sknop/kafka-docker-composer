from __future__ import print_function

import argparse
import re
import os.path
import sys

# constants

TEMPLATES_DIR="templates"
BROKER_TEMPLATE=os.path.join(TEMPLATES_DIR,"kafka.template")
ZOOKEEPER_TEMPLATE=os.path.join(TEMPLATES_DIR,"zookeeper.template")
DOCKER_COMPOSE_TEMPLATE=os.path.join(TEMPLATES_DIR,"docker-compose.template")
DOCKER_COMPOSE_FILE="docker-compose.yaml"

# known variables to fill
# single (broker)
#
BROKER_NAME="{{broker-name}}"
BROKER_ID="{{broker-id}}"
BROKER_PORT="{{broker-port}}"
BROKER_PORT_INTERNAL="{{broker-port-internal}}"
BROKER_PORT_EXTERNAL="{{broker-port-external}}"
BROKER_ADVERTISED_PORT_EXTERNAL="{{broker-advertised-port-external}}"
BROKER_ADVERTISED_PORT_INTERNAL="{{broker-advertised-port-internal}}"
BROKER_JMX_PORT="{{broker-jmx-port}}"
BROKER_RACK="{{broker-rack}}"

#
# single (zookeeper)
#
ZOOKEEPER_NAME="{{zookeeper-name}}"
ZOOKEEPER_ID="{{zookeeper-id}}"
ZOOKEEPER_PORT="{{zookeeper-port}}"
ZOOKEEPER_JMX_PORT="{{zookeeper-jmx-port}}"
ZOOKEEPER_GROUPS="{{zookeeper-groups}}"

#
# services
#
ZOOKEEPER_SERVICES="{{zookeeper-services}}"
BROKER_SERVICES="{{broker-services}}"
#
# multiple
#
ZOOKEEPER_CONTAINERS="{{zookeeper-containers}}" # array of dependencies
ZOOKEEPER_PORTS="{{zookeeper-ports}}" # host:port[,host:port]*
ZOOKEEPER_INTERNAL_PORTS="{{zookeeper-internal-ports}}" # host:2888:3888[;host:2888:3888]*



class YamlGenerator:
    def __init__(self, args):
        self.args = args

        with open(self.args.docker_compose_template) as f:
            self.master_template = f.read()

        with open(self.args.broker_template) as f:
            self.broker_template = f.read()

        with open(self.args.zookeeper_template) as f:
            self.zookeeper_template = f.read()

        self.zookeeper_offset = YamlGenerator.find_offset(self.master_template, ZOOKEEPER_SERVICES)
        self.broker_offset = YamlGenerator.find_offset(self.master_template, BROKER_SERVICES)
        self.depends_offset = YamlGenerator.find_offset(self.broker_template, ZOOKEEPER_CONTAINERS)

        self.zookeeper_containers = ""
        self.zookeeper_ports = ""
        self.zookeeper_internal_ports = ""
        self.zookeeper_groups = ""

    def generate(self):
        zookeeper_services = self.generate_zookeeper_services()
        broker_services = self.generate_broker_services()

        zookeeper_placeholder = self.zookeeper_offset + ZOOKEEPER_SERVICES
        broker_placeholder = self.broker_offset + BROKER_SERVICES

        output_file = self.master_template
        output_file = output_file.replace(zookeeper_placeholder, zookeeper_services)
        output_file = output_file.replace(broker_placeholder, broker_services)

        with open(self.args.docker_compose_file, "w") as yaml_file:
            yaml_file.write(output_file)

    def generate_zookeeper_services(self):
        zookeepers = []

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
                zks = ":".join([ str(1 + x + group * zookeepers_per_group) for x in range(zookeepers_per_group)])
                groups.append(zks)

            self.zookeeper_groups = ";".join(groups)

        for zk in range(1,self.args.zookeepers + 1):
            zookeeper = {}
            zookeeper[ZOOKEEPER_NAME] = "zookeeper" + str(zk)
            zookeeper[ZOOKEEPER_ID] = str(zk)
            zookeeper[ZOOKEEPER_PORT] = "2181"
            zookeeper[ZOOKEEPER_JMX_PORT] = "9999"
            zookeeper[ZOOKEEPER_GROUPS] = self.zookeeper_groups

            zookeepers.append(zookeeper)

        self.zookeeper_containers = "\n{}".format(self.depends_offset).\
            join( [ '- ' + x[ZOOKEEPER_NAME] for x in zookeepers ] )
        self.zookeeper_ports = ",".join( [ x[ZOOKEEPER_NAME] + ':' + x[ZOOKEEPER_PORT] for x in zookeepers ] )
        self.zookeeper_internal_ports = ";".join( [ x[ZOOKEEPER_NAME] + ":2888:3888" for x in zookeepers ] )

        for zk in zookeepers:
            zk[ZOOKEEPER_INTERNAL_PORTS] = self.zookeeper_internal_ports

        services = "\n".join( [ self.generate_one_zookeeper_service(x) for x in zookeepers ] )

        return services

    def generate_one_zookeeper_service(self, zookeeper):
        service = self.zookeeper_template
        for key,value in zookeeper.items():
            service = service.replace(key, value)

        lines = service.split('\n')
        result = [ self.zookeeper_offset + line for line in lines ]

        return "\n".join(result)

    def generate_broker_services(self):
        brokers = []

        rack = 0

        for id in range(1,self.args.brokers + 1):
            port = 9090 + id
            internal_port = 19090 + id

            broker = {}
            broker[BROKER_NAME] = "kafka" + str(id)
            broker[BROKER_ID] = str(id)
            broker[BROKER_PORT] = str(port)
            broker[BROKER_PORT_INTERNAL] = "{}:{}".format(broker[BROKER_NAME],str(internal_port))
            broker[BROKER_PORT_EXTERNAL] = "{}:{}".format(broker[BROKER_NAME],str(port))
            broker[BROKER_ADVERTISED_PORT_INTERNAL] = "{}:{}".format(broker[BROKER_NAME],str(internal_port))
            broker[BROKER_ADVERTISED_PORT_EXTERNAL] = "{}:{}".format("localhost",str(port))
            broker[BROKER_JMX_PORT] = "9999"
            broker[ZOOKEEPER_CONTAINERS] = self.zookeeper_containers
            broker[ZOOKEEPER_PORTS] = self.zookeeper_ports
            broker[BROKER_RACK] = str(rack)

            brokers.append(broker)

            rack = YamlGenerator.next_rack(rack, self.args.racks)

        services = "\n".join( [ self.generate_one_broker_service(x) for x in brokers ] )

        return services

    def generate_one_broker_service(self, broker):
        service = self.broker_template
        for key,value in broker.items():
            service = service.replace(key,value)

        lines = service.split('\n')
        result = [ self.broker_offset + line for line in lines ]

        return "\n".join(result)

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
        raise Exception("Offset for placeholder {} not found".format(placeholder))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Kafka docker-compose Generator")

    # required without defaults
    parser.add_argument('-b', '--brokers', required=True, type=int, help="Number of Brokers")
    parser.add_argument('-z', '--zookeepers', required=True, type=int, help="Number of ZooKeepers")

    # optional with defaults
    parser.add_argument('--docker-compose-template', default=DOCKER_COMPOSE_TEMPLATE,
                        help="Template file for docker-compose, default \"{}\"".format(DOCKER_COMPOSE_TEMPLATE))
    parser.add_argument('--broker-template', default=BROKER_TEMPLATE,
                        help="Template file for brokers, default \"{}\"".format(BROKER_TEMPLATE))
    parser.add_argument('--zookeeper-template', default=ZOOKEEPER_TEMPLATE,
                        help="Template file for zookeepers, default \"{}\"".format(ZOOKEEPER_TEMPLATE))
    parser.add_argument('--docker-compose-file', default=DOCKER_COMPOSE_FILE,
                        help="Output file for docker-compose, default \"{}\"".format(DOCKER_COMPOSE_FILE))
    parser.add_argument('--racks', type=int, default=1,
                        help="Number of racks among which the brokers will be distributed evenly")
    parser.add_argument('--zookeeper-groups', type=int, default=1,
                        help="Number of zookeeper groups in a hierarchy")

    args = parser.parse_args()

    generator = YamlGenerator(args)
    generator.generate()
