#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
source ${DIR}/../.env
machine=`uname -m`

# Confluent's ubi-based Docker images do not have 'tc' installed
echo
echo "Build custom cp-zookeeper cp-server cp-schema-registry cp-server-connect cp-ksqldb-server cp-enterprise-control-center images with 'tc' installed"
for image in cp-zookeeper cp-server cp-schema-registry cp-server-connect cp-ksqldb-server cp-enterprise-control-center; do
  IMAGENAME=localbuild/${image}-tc:${CONFLUENT_DOCKER_TAG}
  docker buildx build --no-cache --build-arg CP_VERSION=${CONFLUENT_DOCKER_TAG} --build-arg REPOSITORY=${REPOSITORY} --build-arg IMAGE=$image --build-arg MACHINE=${machine} -t $IMAGENAME -f ${DIR}/../Dockerfile .
  docker image inspect $IMAGENAME >/dev/null 2>&1 || \
     { echo "Docker image $IMAGENAME not found. Please troubleshoot and rerun"; exit 1; }
done