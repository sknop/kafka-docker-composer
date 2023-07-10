# kafka-docker-composer
Python script to generate a docker-compose.yaml file based on a Jinja2 template and parameters

**Usage:**

```
usage: kafka_docker_composer.py [-h] [-r RELEASE] [-b BROKERS] [-z ZOOKEEPERS]
                                [-s SCHEMA_REGISTRIES] [-p]
                                [--control-center]
                                [--racks RACKS]
                                [--zookeeper-groups ZOOKEEPER_GROUPS]
                                [-c CONFIG]

Kafka docker-compose Generator

optional arguments:
  -h, --help            show this help message and exit
  -r RELEASE, --release RELEASE (default: 7.4.0)
                        Docker images release
  -b BROKERS, --brokers BROKERS
                        Number of Brokers [1]
  -z ZOOKEEPERS, --zookeepers ZOOKEEPERS
                        Number of ZooKeepers [1]
  -s SCHEMA_REGISTRIES, --schema-registries SCHEMA_REGISTRIES
                        Number of Schema Registry instances [0]
  -p, --prometheus      Include Prometheus [False]
  --control-center      Include Confluent Control Center [False]
  --docker-compose-template DOCKER_COMPOSE_TEMPLATE
                        Template file for docker-compose, default
                        "templates/docker-compose.template"
  --broker-template BROKER_TEMPLATE
                        Template file for brokers, default
                        "templates/kafka.template"
  --zookeeper-template ZOOKEEPER_TEMPLATE
                        Template file for zookeepers, default
                        "templates/zookeeper.template"
  --schema-registry-template SCHEMA_REGISTRY_TEMPLATE
                        Template file for schema registry, default
                        "templates/schema-registry.template"
  --control-center-template CONTROL_CENTER_TEMPLATE
                        Template file for control center, default
                        "templates/control-center.template"
  --prometheus-template PROMETHEUS_TEMPLATE
                        Template file for prometheus, default
                        "templates/prometheus.template"
  --prometheus-config-template PROMETHEUS_CONFIG_TEMPLATE
                        Template file for prometheus config, default
                        "templates/prometheus.yml.template"
  --docker-compose-file DOCKER_COMPOSE_FILE
                        Output file for docker-compose, default "docker-
                        compose.yaml"
  --broker-internal-protocol BROKER_INTERNAL_PROTOCOL
                        Internal protocol used (default PLAINTEXT)
  --broker-external-protocol BROKER_EXTERNAL_PROTOCOL
                        External protocol used (default PLAINTEXT)
  --racks RACKS         Number of racks among which the brokers will be
                        distributed evenly
  --zookeeper-groups ZOOKEEPER_GROUPS
                        Number of zookeeper groups in a hierarchy
  -c CONFIG, --config CONFIG
                        Properties config file, values will be overriden by
                        command line arguments
```

**Example:**
```
> python3 kafka_docker_composer.py -b 4 -z 3
> docker-compose up -d
```

There is a master template ```templates/docker-compose.template``` that pulls in the zookeeper and broker templates.
Create new templates if you want to add security or additional features, or change the docker image 
(by default I use the confluent docker images).

If you want to use Prometheus and Grafana, use the option `-p`. This also generates the appropriate Prometheus 
configuration file from a template to reference all Kafka brokers. This template can also be overridden with the
option `--prometheus-config-template`.

Grafana is set up but no dashboards are defined. Examples dashboards can be found in the `provisioning/dashboards`
folder and can be accessed in Grafana by clicking on the arrow in the top-left corner to the right of HOME and
clicking on *Import dashboard* in the menu to load up a dashboard from your local directory (not the container).

 
It is now also possible to use a config file instead of specifying all parameters by hand for 
reproducabilty and ease of use. Specify the config file with the option `-c` or `--config`. 

**TODO:**
* Add connect
* Add templates with security
