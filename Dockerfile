# leverage the renci python base image
FROM renciorg/renci-python-image:v0.0.1

#Set the branch
ARG BRANCH_NAME=main

# install basic tools
RUN apt-get update

# make a directory for the repo
RUN mkdir /repo

# go to the directory where we are going to upload the repo
WORKDIR /repo

# get the latest code
RUN git clone --branch $BRANCH_NAME --single-branch https://github.com/TranslatorSRI/NameResolution.git

# go to the repo dir
WORKDIR /repo/NameResolution

# install requirements
RUN pip install -r requirements.txt

# expose the default port
EXPOSE 2433

RUN chmod 777 -R .

USER nru

# start the service entry point
ENTRYPOINT ["bash", "main.sh"]