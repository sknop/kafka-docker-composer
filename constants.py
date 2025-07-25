RANDOM_UUID = "Nk018hRAQFytWskYqtQduw"

DEFAULT_RELEASE = "8.0.0"
CONTROL_CENTER_NEXT_GEN_RELEASE = "2.2.0"
CONFLUENT_REPOSITORY = "confluentinc"
CONFLUENT_CONTAINER = "cp-server"
CONFLUENT_KAFKA_CLUSTER_CMD = "/usr/bin/kafka-cluster"

APACHE_REPOSITORY = "apache"
APACHE_CONTAINER = "kafka"
OSK_KAFKA_CLUSTER_CMD = "/opt/kafka/bin/kafka-cluster.sh"


LOCALBUILD = "localbuild"
JMX_PROMETHEUS_JAVA_AGENT_VERSION = "1.3.0"
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
