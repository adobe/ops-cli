FROM centos:latest

ENV PATH "$PATH:/"

RUN yum install -y epel-release && \
    yum install -y python-pip autoconf gcc python-devel libffi-devel openssl-devel unzip && \
    yum clean all && \
    pip install virtualenv

COPY requirements.txt requirements.txt
RUN virtualenv /pythonenv && \
    /pythonenv/bin/pip install -r requirements.txt && \
    /pythonenv/bin/pip install pytest

# Can be overwritten with `--build-arg` argument to `docker build`
# https://docs.docker.com/engine/reference/builder/#arg
ARG TERRAFORM_VERSION=0.8.5
RUN curl -OL https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip

ENV PATH "/pythonenv/bin:$PATH"
