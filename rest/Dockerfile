FROM python:3.6-alpine
LABEL MAINTAINER="martin.owen22@gmail.com"

RUN  pip3 install redis minio flask jsonpickle

WORKDIR /srv

COPY    rest-server.py /srv
COPY    minio_plugin.py /srv

ENTRYPOINT ["/bin/bash", "--login", "-c"]
CMD ["python3, rest-server.py"]
