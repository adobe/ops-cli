FROM python:3.7-alpine3.10 AS compile-image
ARG TERRAFORM_VERSION="0.12.6"
ARG AZURE_CLI_VERSION="2.0.67"

ENV BOTO_CONFIG=/dev/null
COPY . /sources/
WORKDIR /sources

RUN wget -q -O terraform.zip https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
    && unzip terraform.zip -d /usr/local/bin \
    && rm -rf terraform.zip
RUN apk add --virtual=build bash gcc libffi-dev musl-dev openssl-dev make git
RUN ln -s /usr/local/bin/python /usr/bin/python
RUN pip --no-cache-dir install virtualenv \
    && virtualenv /azure-cli \
    && source /azure-cli/bin/activate \
    && pip install azure-cli==${AZURE_CLI_VERSION} \
    && deactivate
RUN bash build_scripts/freeze_requirements.sh
RUN bash build_scripts/run_tests.sh
RUN bash build_scripts/build_package.sh
RUN apk del --purge build


FROM python:3.7-alpine3.10
ARG TERRAFORM_VERSION="0.12.6"
ARG VAULT_VERSION="1.1.3"
ARG KUBECTL_VERSION="v1.17.0"
ARG AWS_IAM_AUTHENTICATOR_VERSION="1.13.7/2019-06-11"
ARG HELM_VERSION="v2.14.3"
ARG HELM_FILE_VERSION="v0.81.3"
ARG HELM_DIFF_VERSION="2.11.0%2B5"


COPY --from=compile-image /sources/dist /dist

RUN adduser ops -Du 2342 -h /home/ops \
    && ln -s /usr/local/bin/python /usr/bin/python \
    && apk add --no-cache bash zsh ca-certificates curl jq openssh-client git \
    && apk add --virtual=build gcc libffi-dev musl-dev openssl-dev make \
    # Install ops python package
    && pip --no-cache-dir install --upgrade /dist/ops-*.tar.gz \
    && rm -rf /dist \
    # Dry-run
    && ops --verbose -h \
    && apk del --purge build \
    && wget -q https://storage.googleapis.com/kubernetes-release/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl -O /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && wget -q https://storage.googleapis.com/kubernetes-helm/helm-${HELM_VERSION}-linux-amd64.tar.gz -O - | tar -xzO linux-amd64/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm \
    && wget -q -O terraform.zip https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
    && unzip terraform.zip -d /usr/local/bin \
    && rm -rf terraform.zip \
    && mkdir -p  ~/.terraform.d/plugins && wget -q -O ~/.terraform.d/plugins/terraform-provider-vault https://github.com/amuraru/terraform-provider-vault/releases/download/vault-namespaces/terraform-provider-vault \
    && chmod 0755 ~/.terraform.d/plugins/terraform-provider-vault \
    && wget -q -O vault.zip https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip \
    && unzip vault.zip -d /usr/local/bin \
    && rm -rf vault.zip \
    && wget -q https://amazon-eks.s3-us-west-2.amazonaws.com/${AWS_IAM_AUTHENTICATOR_VERSION}/bin/linux/amd64/aws-iam-authenticator -O /usr/local/bin/aws-iam-authenticator \
    && chmod +x /usr/local/bin/aws-iam-authenticator \
    && wget -q https://github.com/roboll/helmfile/releases/download/${HELM_FILE_VERSION}/helmfile_linux_amd64 -O /usr/local/bin/helmfile \
    && chmod +x /usr/local/bin/helmfile
# Fix https://github.com/kubernetes-client/python-base/pull/126/files
COPY build_scripts/patches/kube_config.py /usr/local/lib/python3.7/site-packages/kubernetes/config/kube_config.py

# install utils under `ops` user
USER ops
ENV HOME=/home/ops
WORKDIR /home/ops

RUN helm init --client-only

RUN curl -sSL https://github.com/databus23/helm-diff/releases/download/v${HELM_DIFF_VERSION}/helm-diff-linux.tgz | tar xvz -C $(helm home)/plugins


USER root
RUN HELM_HOME=/home/ops/.helm helm plugin install https://github.com/futuresimple/helm-secrets
RUN HELM_HOME=/home/ops/.helm helm plugin install https://github.com/rimusz/helm-tiller
RUN chown -R ops:ops /home/ops/.helm

COPY --from=compile-image /azure-cli /home/ops/.local/azure-cli
COPY build_scripts/bin/az /home/ops/bin/

RUN touch /home/ops/.zshrc

USER ops
ENV PATH="/home/ops/bin:${PATH}"
ENV PS1="%d $ "
CMD /bin/zsh
