# leverage the renci python base image
FROM renciorg/renci-python-image:latest

# install basic tools
RUN apt update
RUN apt upgrade -y

# Make a home directory for the non-root user.
RUN mkdir /home/nru
RUN chown nru /home/nru

# make a directory for the repo
RUN mkdir /repo

# go to the directory where we are going to upload the repo
WORKDIR /repo
RUN mkdir NameResolution
RUN chown nru NameResolution
USER nru

# add the current code
COPY . /repo/NameResolution

# go to the repo dir
WORKDIR /repo/NameResolution

# install requirements
ENV PATH="${PATH}:/home/nru/.local/bin"
RUN pip install -r requirements.txt

# expose the default port
EXPOSE 2433

# start the service entry point
ENTRYPOINT ["bash", "main.sh"]
