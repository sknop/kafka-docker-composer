ARG REPOSITORY
ARG IMAGE
ARG CP_VERSION

FROM $REPOSITORY/$IMAGE:$CP_VERSION

#ARG TARGETPLATFORM
#ARG BUILDPLATFORM
#RUN echo "I am running on $BUILDPLATFORM, building for $TARGETPLATFORM"

USER root
RUN yum install -y \
     libmnl \
     findutils \
     which
RUN wget https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/iproute-tc-5.18.0-1.1.0.1.el8_8.aarch64.rpm
RUN rpm -i --nodeps --nosignature https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/iproute-tc-5.18.0-1.1.0.1.el8_8.aarch64.rpm
RUN wget https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/iptables-1.8.4-24.0.1.el8.aarch64.rpm
RUN rpm -i --nodeps --nosignature https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/iptables-1.8.4-24.0.1.el8.aarch64.rpm

# Dependencies

RUN wget https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libbpf-0.6.0-6.el8.aarch64.rpm
RUN rpm -i --nodeps --nosignature https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libbpf-0.6.0-6.el8.aarch64.rpm
RUN wget https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/iptables-libs-1.8.4-24.0.1.el8.aarch64.rpm
RUN rpm -i --nodeps --nosignature https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/iptables-libs-1.8.4-24.0.1.el8.aarch64.rpm
RUN wget https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libnftnl-1.1.5-5.el8.aarch64.rpm
RUN rpm -i --nodeps --nosignature https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libnftnl-1.1.5-5.el8.aarch64.rpm
RUN wget https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libnfnetlink-1.0.1-13.el8.aarch64.rpm
RUN rpm -i --nodeps --nosignature https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libnfnetlink-1.0.1-13.el8.aarch64.rpm
RUN wget https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libnetfilter_conntrack-1.0.6-5.el8.aarch64.rpm
RUN rpm -i --nodeps --nosignature https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libnetfilter_conntrack-1.0.6-5.el8.aarch64.rpm

USER appuser
