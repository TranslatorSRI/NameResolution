# leverage the renci python base image
FROM renciorg/renci-python-image:v0.0.1

# set up working directory
RUN mkdir /home/nru
WORKDIR /home/nru

# make sure all is writeable for the nru USER later on
RUN chmod -R 777 .

# install python package requirements
ADD ./requirements.txt /home/nru/requirements.txt
RUN pip install -r /home/nru/requirements.txt --src /usr/local/src

USER nru

# set up source
ADD ./api /home/nru/api
ADD ./main.sh /home/nru/main.sh

EXPOSE 2433

# set up entrypoint
ENTRYPOINT ["bash", "main.sh"]
