# kafka-docker-composer
Python script to generate a docker-compose.yaml file based on templates and parameters

**Usage:**

```
python3 kafka_docker_composer.py -h
usage: kafka_docker_composer.py [-h] -b BROKERS -z ZOOKEEPERS
                                [--docker-compose-template DOCKER_COMPOSE_TEMPLATE]
                                [--broker-template BROKER_TEMPLATE]
                                [--zookeeper-template ZOOKEEPER_TEMPLATE]
                                [--docker-compose-file DOCKER_COMPOSE_FILE]

Kafka docker-compose Generator

optional arguments:
  -h, --help            show this help message and exit
  -b BROKERS, --brokers BROKERS
                        Number of Brokers
  -z ZOOKEEPERS, --zookeepers ZOOKEEPERS
                        Number of ZooKeepers
  --docker-compose-template DOCKER_COMPOSE_TEMPLATE
                        Template file for docker-compose, default
                        "templates/docker-compose.template"
  --broker-template BROKER_TEMPLATE
                        Template file for brokers, default
                        "templates/kafka.template"
  --zookeeper-template ZOOKEEPER_TEMPLATE
                        Template file for zookeepers, default
                        "templates/zookeeper.template"
  --docker-compose-file DOCKER_COMPOSE_FILE
                        Output file for docker-compose, default "docker-
                        compose.yaml"
  -c CONFIG, --config CONFIG
                        Properties config file, values will be overriden by
                        command line arguments

```

**Example:**
```
> python3 kafka_docker_composer.py -b 4 -z3
> docker-compose up -d
```

There is a master template ```templates/docker-compose.template``` that pulls in the zookeeper and broker templates.
Create new templates if you want to add security or additional features, or change the docker image 
(by default I use the confluent docker images).

It is now also possible to use a config file instead of specifying all parameters by hand for 
reproducabilty and ease of use.

**TODO:**
. Add schema registry and connect
. Add templates with security
