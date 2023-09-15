# Kafka Connect Suite of JMS Connectors
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bhttps%3A%2F%2Fgithub.com%2Fconfluentinc%2Fkafka-connect-jms.svg?type=shield)](https://app.fossa.io/projects/git%2Bhttps%3A%2F%2Fgithub.com%2Fconfluentinc%2Fkafka-connect-jms?ref=badge_shield)


*kafka-connect-jms* is a suite of [Kafka Connectors](http://kafka.apache.org/documentation.html#connect)
designed to copy messages from JMS brokers, such as [ActiveMQ](http://activemq.apache.org/), [IBM MQ](https://www-03.ibm.com/software/products/en/ibm-mq),
[TIBCO EMS](https://www.tibco.com/products/tibco-enterprise-message-service), and [Solace Appliance](https://docs.solace.com/Solace-Messaging-APIs/Solace-APIs-Overview.htm).

This suite contains three modules:

* `kafka-connect-jms` - The generic JMS source connector that works with [ActiveMQ](http://activemq.apache.org/), [IBM MQ](https://www-03.ibm.com/software/products/en/ibm-mq),
[TIBCO EMS](https://www.tibco.com/products/tibco-enterprise-message-service), and [Solace Appliance](https://docs.solace.com/Solace-Messaging-APIs/Solace-APIs-Overview.htm)
* `kafka-connect-ibmmq` - A specialization of the source connector that works with [IBM MQ](https://www-03.ibm.com/software/products/en/ibm-mq)
and includes IBM MQ-specific configuration properties.
* `kafka-connect-activemq` - A specialization of the source connector that works with [ActiveMQ](http://activemq.apache.org/)
and includes ActiveMQ-specific configuration properties.

In the future we may choose to add other modules for specific JMS broker systems.


# Development

To build a development version you'll need a recent version of Kafka
as well as a set of upstream Confluent projects, which you'll have to build from their appropriate snapshot branch.

You can build *kafka-connect-jms* with Maven using the standard lifecycle phases.


# Contribute

- Source Code: https://github.com/confluentinc/kafka-connect-jms
- Issue Tracker: https://confluentinc.atlassian.net/projects/CC/issues


[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bhttps%3A%2F%2Fgithub.com%2Fconfluentinc%2Fkafka-connect-jms.svg?type=shield)](https://app.fossa.io/projects/git%2Bhttps%3A%2F%2Fgithub.com%2Fconfluentinc%2Fkafka-connect-jms?ref=badge_shield)