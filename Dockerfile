FROM costimuraru/linuxbrew-centos7:1.0.0

USER root
RUN rm /bin/sh && ln -s /bin/bash /bin/sh
RUN echo 'brew install $1 && sudo rm -rf /home/linuxbrew/.cache' > /usr/local/bin/brew-install
RUN chmod +x /usr/local/bin/brew-install
USER linuxbrew

RUN brew-install aws-iam-authenticator
ENV HOMEBREW_NO_AUTO_UPDATE=1
RUN brew-install terraform
RUN brew-install wget
RUN brew-install kubernetes-helm
RUN brew-install kubectl
RUN brew-install jq
RUN brew-install python2

RUN pip2 install -U virtualenv
RUN virtualenv ops
RUN source ops/bin/activate
RUN pip2 install --upgrade https://github.com/adobe/ops-cli/releases/download/0.25/ops-0.25.tar.gz
