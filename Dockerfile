ARG REPOSITORY
ARG IMAGE
ARG CP_VERSION
ARG MACHINE
ARG TARGETPLATFORM
ARG BUILDPLATFORM

FROM $REPOSITORY/$IMAGE:$CP_VERSION AS base
USER root
RUN yum install -y \
     libmnl \
     findutils \
     which

FROM base AS build-arm64
ENV IPROUTE=https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/iproute-tc-5.18.0-1.1.0.1.el8_8.aarch64.rpm
ENV IPTABLES=https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/iptables-1.8.4-24.0.1.el8.aarch64.rpm
ENV LIBBPF=https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libbpf-0.6.0-6.el8.aarch64.rpm
ENV IPTABLES_LIBS=https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/iptables-libs-1.8.4-24.0.1.el8.aarch64.rpm
ENV LIBNFTNL=https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libnftnl-1.2.2-3.el8.aarch64.rpm
ENV LIBFNETLINK=https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libnfnetlink-1.0.1-13.el8.aarch64.rpm
ENV LIBFNETLINK_CONNTRACK=https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/aarch64/getPackage/libnetfilter_conntrack-1.0.6-5.el8.aarch64.rpm

FROM base AS build-x86_64
ENV IPROUTE=https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/x86_64/getPackage/iproute-tc-5.18.0-1.1.0.1.el8_8.x86_64.rpm
ENV IPTABLES=https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/x86_64/getPackage/iptables-1.8.4-24.0.1.el8.x86_64.rpm
ENV LIBBPF=https://yum.oracle.com/repo/OracleLinux/OL8/UEKR7/x86_64/getPackage/libbpf-0.6.0-6.el8.x86_64.rpm
ENV IPTABLES_LIBS=https://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/x86_64/getPackage/iptables-libs-1.8.4-24.0.1.el8.x86_64.rpm
ENV LIBNFTNL=https://dl.rockylinux.org/pub/rocky/8/BaseOS/x86_64/os/Packages/l/libnftnl-1.2.2-3.el8.x86_64.rpm
ENV LIBFNETLINK=https://repo.almalinux.org/almalinux/8/BaseOS/x86_64/os/Packages/libnfnetlink-1.0.1-13.el8.x86_64.rpm
ENV LIBFNETLINK_CONNTRACK=https://repo.almalinux.org/almalinux/8/BaseOS/x86_64/os/Packages/libnetfilter_conntrack-1.0.6-5.el8.x86_64.rpm

FROM build-${MACHINE} AS final
RUN wget ${IPROUTE}
RUN rpm -i --nodeps --nosignature ${IPROUTE}
RUN wget ${IPTABLES}
RUN rpm -i --nodeps --nosignature ${IPTABLES}

# Dependencies

RUN wget ${LIBBPF}
RUN rpm -i --nodeps --nosignature ${LIBBPF}
RUN wget ${IPTABLES_LIBS}
RUN rpm -i --nodeps --nosignature ${IPTABLES_LIBS}
RUN wget ${LIBNFTNL}
RUN rpm -i --nodeps --nosignature  ${LIBNFTNL}
RUN wget ${LIBFNETLINK}
RUN rpm -i --nodeps --nosignature ${LIBFNETLINK}
RUN wget ${LIBFNETLINK_CONNTRACK}
RUN rpm -i --nodeps --nosignature ${LIBFNETLINK_CONNTRACK}

USER appuser
