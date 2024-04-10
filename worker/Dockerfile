FROM tensorflow/tensorflow
RUN  pip3 install pillow numpy scipy redis minio flask 

WORKDIR /srv
     
RUN     curl -k https://www.vlfeat.org/matconvnet/models/imagenet-vgg-verydeep-19.mat --output /srv/imagenet-vgg-verydeep-19.mat
# takes ~ 2 minutes
ADD     neural-style /srv
COPY    worker-server.py /srv
COPY    worker-listener.py /srv
COPY    minio_plugin.py /srv

ENTRYPOINT ["/bin/bash", "--login", "-c"]