FROM python:3.12.3-alpine3.18 AS compile-image
ARG TARGETARCH
ARG TARGETPLATFORM
ARG TERRAFORM_VERSION="0.12.31"
ARG AZURE_CLI_VERSION="2.0.67"

ENV BOTO_CONFIG=/dev/null
COPY . /sources/
WORKDIR /sources

# Install terraform (needed for tests in compile stage)
RUN wget -q -O terraform.zip https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TARGETARCH}.zip \
    && unzip terraform.zip -d /usr/local/bin \
    && rm -rf terraform.zip
RUN apk add --virtual=build bash gcc libffi-dev musl-dev openssl-dev make git
RUN ln -s /usr/local/bin/python /usr/bin/python
RUN pip --no-cache-dir install virtualenv \
    && virtualenv /azure-cli \
    && source /azure-cli/bin/activate \
    && python -m pip install --upgrade pip \
    && env CRYPTOGRAPHY_DONT_BUILD_RUST=1 pip install azure-cli==${AZURE_CLI_VERSION} \
    && deactivate
RUN bash build_scripts/freeze_requirements.sh  
RUN bash build_scripts/run_tests.sh
RUN bash build_scripts/build_package.sh
RUN apk del --purge build


FROM python:3.12.3-alpine3.18
ARG TARGETARCH
ARG TARGETPLATFORM
ARG TERRAFORM_VERSION="0.12.31"
ARG VAULT_VERSION="1.1.3"
ARG KUBECTL_VERSION="v1.17.0"
ARG AWS_IAM_AUTHENTICATOR_VERSION="1.13.7/2019-06-11"
ARG HELM_VERSION="v3.16.3"
ARG HELM_FILE_VERSION="1.1.8"
ARG HELM_DIFF_VERSION="2.11.0%2B5"


COPY --from=compile-image /sources/dist /dist

RUN adduser ops -Du 2342 -h /home/ops \
    && ln -s /usr/local/bin/python /usr/bin/python \
    && /usr/bin/python -m pip install --upgrade pip \
    && apk add --no-cache bash zsh ca-certificates curl jq openssh-client git \
    && apk add --virtual=build gcc libffi-dev musl-dev openssl-dev make \
    # Install ops python package
    && env CRYPTOGRAPHY_DONT_BUILD_RUST=1 pip --no-cache-dir install --upgrade /dist/ops*.tar.gz \
    && rm -rf /dist \
    # Dry-run
    && ops --verbose -h \
    && apk del --purge build

RUN wget -q https://storage.googleapis.com/kubernetes-release/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl -O /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl

RUN wget -q https://get.helm.sh/helm-${HELM_VERSION}-linux-${TARGETARCH}.tar.gz -O - | tar -xzO linux-${TARGETARCH}/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm

RUN wget -q -O terraform.zip https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TARGETARCH}.zip \
    && unzip terraform.zip -d /usr/local/bin \
    && rm -rf terraform.zip
    
RUN wget -q -O vault.zip https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_${TARGETARCH}.zip \
    && unzip vault.zip -d /usr/local/bin \
    && rm -rf vault.zip
    
RUN wget -q https://amazon-eks.s3-us-west-2.amazonaws.com/${AWS_IAM_AUTHENTICATOR_VERSION}/bin/linux/${TARGETARCH}/aws-iam-authenticator -O /usr/local/bin/aws-iam-authenticator \
    && chmod +x /usr/local/bin/aws-iam-authenticator

RUN wget -q https://github.com/helmfile/helmfile/releases/download/v${HELM_FILE_VERSION}/helmfile_${HELM_FILE_VERSION}_linux_${TARGETARCH}.tar.gz -O - | tar -xzO helmfile > /usr/local/bin/helmfile \
    && chmod +x /usr/local/bin/helmfile

# install utils under `ops` user
USER ops
ENV HOME=/home/ops
WORKDIR /home/ops

USER root
RUN helm plugin install https://github.com/databus23/helm-diff --version v3.9.11
RUN helm plugin install https://github.com/jkroepke/helm-secrets --version v3.8.2
RUN helm plugin install https://github.com/rimusz/helm-tiller  # Obsolete in Helm 3


COPY --from=compile-image /azure-cli /home/ops/.local/azure-cli
COPY build_scripts/bin/az /home/ops/bin/

RUN touch /home/ops/.zshrc

USER ops
ENV PATH="/home/ops/bin:${PATH}"
ENV PS1="%d $ "
CMD /bin/zsh
