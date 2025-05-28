from .generator import Generator
from constants import *

import sys

class ZooKeeperGenerator(Generator):
    def __init__(self, base):
        super().__init__(base)


    def calculate_zookeeper_groups(self):
        zookeeper_groups = ""
        if self.base.args.zookeeper_groups > 1:
            zookeepers_per_group = self.base.args.zookeepers // self.base.args.zookeeper_groups
            rest = self.base.args.zookeepers % self.base.args.zookeeper_groups
            if rest != 0:
                print("ERROR, no equal distribution of zookeeper nodes across groups #ZK {} #GR {} rest {} "
                      .format(self.base.args.zookeepers, self.base.args.zookeeper_groups, rest))
                sys.exit(-1)

            groups = []
            for group in range(self.base.args.zookeeper_groups):
                zks = ":".join([str(1 + x + group * zookeepers_per_group) for x in range(zookeepers_per_group)])
                groups.append(zks)

            zookeeper_groups = ";".join(groups)

        return zookeeper_groups

    def generate(self):
        zookeeper_groups = self.calculate_zookeeper_groups()

        zookeepers = []
        zookeeper_servers = []

        targets = []
        job = {
            "name": "zookeeper",
            "scrape_interval": "5s",
            "targets": targets
        }

        for zk in range(1, self.base.args.zookeepers + 1):
            zookeeper_external_port = 2180 + zk

            zookeeper = {}

            name = self.base.create_name("zookeeper", zk)
            zookeeper["name"] = name
            zookeeper["hostname"] = name
            zookeeper["container_name"] = name

            targets.append(f"{name}:{JMX_PORT}")

            zookeeper_servers.append(name + ":2888:3888")

            zookeeper["image"] = f"{self.base.repository}/cp-zookeeper{self.base.tc}:" + self.base.args.release

            jmx_port = self.base.next_jmx_external_port()

            environment = {
                "ZOOKEEPER_SERVER_ID": zk,
                "ZOOKEEPER_CLIENT_PORT": ZOOKEEPER_PORT,
                "ZOOKEEPER_TICK_TIME": 2000,
                "KAFKA_JMX_PORT": jmx_port,
                "KAFKA_JMX_HOSTNAME": "localhost",
                "KAFKA_OPTS": JMX_PROMETHEUS_JAVA_AGENT + ZOOKEEPER_JMX_CONFIG
            }

            if self.base.args.zookeeper_groups > 1:
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
                self.base.next_agent_port(): JMX_PORT
            }

            zookeepers.append(zookeeper)

        zk_servers = ";".join(zookeeper_servers)
        for zk in zookeepers:
            zk["environment"]["ZOOKEEPER_SERVERS"] = zk_servers

        self.base.zookeepers = ",".join([z["name"] + ":" + ZOOKEEPER_PORT for z in zookeepers])

        self.base.zookeeper_containers = [z["name"] for z in zookeepers]

        if self.base.args.zookeepers > 0:
            self.base.prometheus_jobs.append(job)

        return zookeepers