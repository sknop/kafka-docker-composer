# kafka-docker-composer
Python script to generate a docker-compose.yaml file based on a Jinja2 template and parameters

**Usage:**

```
usage: kafka_docker_composer.py [-h] [-r RELEASE] [-b BROKERS] [-z ZOOKEEPERS] [-c CONTROLLERS] [-s SCHEMA_REGISTRIES] [--control-center] [--uuid UUID] [-p] [--kafka-container KAFKA_CONTAINER] [--racks RACKS]
                                [--zookeeper-groups ZOOKEEPER_GROUPS] [--docker-compose-file DOCKER_COMPOSE_FILE] [--config CONFIG]

Kafka docker-compose Generator

options:
  -h, --help            show this help message and exit
  -r RELEASE, --release RELEASE
                        Docker images release [7.4.0]
  -b BROKERS, --brokers BROKERS
                        Number of Brokers [1]
  -z ZOOKEEPERS, --zookeepers ZOOKEEPERS
                        Number of ZooKeepers [0] - mutually exclusive with controllers
  -c CONTROLLERS, --controllers CONTROLLERS
                        Number of Kafka Connector instances [0] - mutually exclusive with zookeepers
  -C CONNECTS, --connect CONNECTS
                        Number of Kafka Connect instances [0]
  -s SCHEMA_REGISTRIES, --schema-registries SCHEMA_REGISTRIES
                        Number of Schema Registry instances [0]
  --control-center      Include Confluent Control Center [False]
  --uuid UUID           UUID of the cluster [Nk018hRAQFytWskYqtQduw]
  -p, --prometheus      Include Prometheus [False]
  --kafka-container KAFKA_CONTAINER
                        Container used for Kafka, default [cp-server]
  --racks RACKS         Number of racks among which the brokers will be distributed evenly [1]
  --zookeeper-groups ZOOKEEPER_GROUPS
                        Number of zookeeper groups in a hierarchy [1]
  --docker-compose-file DOCKER_COMPOSE_FILE
                        Output file for docker-compose, default [docker-compose.yaml]
  --config CONFIG       Properties config file, values will be overriden by command line arguments
```

**Examples:**
```
> python3 kafka_docker_composer.py -b 4 -z 3 -r 7.3.1
> docker-compose up -d
```

```
> python3 kafka_docker_composer.py --controllers 3 --brokers 3 --schema-registries 2 --control-center  
> docker-compose up -d
```

**TODO:**
* Add security
* Fix dashboards for Grafana

