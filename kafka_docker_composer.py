from __future__ import print_function

import argparse
import re
import os.path

# constants

TEMPLATES_DIR="templates"
BROKER_TEMPLATE=os.path.join(TEMPLATES_DIR,"kafka.template")
ZOOKEEPER_TEMPLATE=os.path.join(TEMPLATES_DIR,"zookeeper.template")
DOCKER_COMPOSE_TEMPLATE=os.path.join(TEMPLATES_DIR,"docker-compose.template")
DOCKER_COMPOSE_FILE="docker-compose.yaml"

# known variables to fill
# single (broker)
#
# {{broker-name}}
# {{broker-id}}
# {{broker-port-internal}}
# {{broker-port-external}}
# {{advertised-broker-port-external}}
# {{advertised-broker-port-internal}}
# {{broker-jmx-port}}
#
# single (zookeeper)
#
# {{zookeeper-name}}
# {{zookeeper-id}}
# {{zookeeper-port}}
# {{zookeeper-jxm-port}}
#
# services
#
ZOOKEEPER_SERVICES="{{zookeeper-services}}"
BROKER_SERVICES="{{broker-services}}"
#
# multiple
#
# {{zookeeper-containers}} - array of dependencies
# {{zookeeper-ports}}      - host:port[,host:port]*
# {{zookeeper-internal-ports}} - host:2888:3888[;host:2888:3888]*
#


class YamlGenerator:
    def __init__(self, args):
        self.args = args

        with open(self.args.docker_compose_template) as f:
            self.master_template = f.read().split("\n")


        self.zookeeper_offset = YamlGenerator.find_offset(self.master_template, ZOOKEEPER_SERVICES)
        self.broker_offset = YamlGenerator.find_offset(self.master_template, BROKER_SERVICES)

    def generate(self):
        with open(self.args.docker_compose_file, "w") as yaml_file:
            for line in self.master_template:
                yaml_file.write(line)
                yaml_file.write('\n')

    def generate_zookeeper_services(self):
        pass

    def generate_broker_services(self):
        pass

    @staticmethod
    def find_offset(template, placeholder):
        pattern = re.compile(r"^(\s*){}".format(placeholder))
        for line in template:
            match = pattern.match(line)
            if match:
                return match.group(1)
        raise Exception("Offset for placeholder {} not found".format(placeholder))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Kafka docker-compose Generator")

    # required without defaults
    parser.add_argument('-b', '--brokers', required=True, type=int, help="Number of Brokers")
    parser.add_argument('-z', '--zookeeper', required=True, type=int, help="Number of ZooKeepers")

    # optional with defaults
    parser.add_argument('--docker-compose-template', default=DOCKER_COMPOSE_TEMPLATE,
                        help="Template file for docker-compose, default \"{}\"".format(DOCKER_COMPOSE_TEMPLATE))
    parser.add_argument('--broker-template', default=BROKER_TEMPLATE,
                        help="Template file for brokers, default \"{}\"".format(BROKER_TEMPLATE))
    parser.add_argument('--zookeeper-template', default=ZOOKEEPER_TEMPLATE,
                        help="Template file for zookeepers, default \"{}\"".format(ZOOKEEPER_TEMPLATE))
    parser.add_argument('--docker-compose-file', default=DOCKER_COMPOSE_FILE,
                        help="Output file for docker-compose, default \"{}\"".format(DOCKER_COMPOSE_FILE))

    parser.add_argument
    args = parser.parse_args()

    generator = YamlGenerator(args)
    generator.generate()
