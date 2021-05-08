FROM python:3.8.1-buster

# install basic tools
RUN apt-get update
RUN apt-get install -yq \
    vim sudo

# set up murphy
ARG UID=1000
ARG GID=1000
RUN groupadd -o -g $GID murphy
RUN useradd -m -u $UID -g $GID -s /bin/bash murphy

# set up requirements
WORKDIR /home/murphy
ADD --chown=murphy:murphy ./requirements.txt /home/murphy/requirements.txt
RUN pip install -r /home/murphy/requirements.txt

# set up source
ADD --chown=murphy:murphy ./api /home/murphy/api
ADD --chown=murphy:murphy ./main.sh /home/murphy/main.sh

# become murphy
ENV HOME=/home/murphy
ENV USER=murphy
USER murphy

# set up entrypoint
ENTRYPOINT ["bash", "main.sh"]
EXPOSE 2433