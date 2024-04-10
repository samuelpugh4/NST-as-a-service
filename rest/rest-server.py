#!/usr/bin/env python3

##
## Sample Flask REST server implementing two methods
##
## Endpoint /api/image is a POST method taking a body containing an image
## It returns a JSON document providing the 'width' and 'height' of the
## image that was provided. The Python Image Library (pillow) is used to
## proce#ss the image
##
## Endpoint /api/add/X/Y is a post or get method returns a JSON body
## containing the sum of 'X' and 'Y'. The body of the request is ignored
##
##
from flask import Flask, request, Response
import jsonpickle, json
import base64
import os
import redis
import sys
import hashlib

import minio_plugin

serverHost = os.getenv("FLASK_HOST") or "0.0.0.0"
serverPort = os.getenv("FLASK_PORT") or "5000"

class RedisClient:
    def __init__(self):
        self.redisHost = os.getenv("REDIS_HOST") or "localhost"
        self.redisPort = os.getenv("REDIS_PORT") or 6379
        self.client = redis.StrictRedis(host=self.redisHost, port=self.redisPort, db=0)

    def log_debug(self, message):
        print("DEBUG:", message, file=sys.stdout)
        self.client.lpush('logging', message)

    def log_info(self, message):
        print("INFO:", message, file=sys.stdout)
        self.client.lpush('logging', message)

redisClient = RedisClient()
# Initialize the Flask application
app = Flask(__name__)

def hash_and_send_to_minio(queue, image):
    hash = hashlib.sha256(image)
    digest = hash.hexdigest()
    print('Sending {} image to minio'.format(queue))
    payload = {'digest': digest, 'bytes': image, 'bucket': queue}
    minio_plugin.dump_to_minio(payload, redisclient=redisClient)
    print('Returning from minio, {} image uploaded in {} bucket'.format(queue, queue))
    return digest

@app.route('/apiv1/style_transfer/', methods=['POST'])
def style_transfer():
    print('In style transfer')
    redisClient.log_info('In style transfer call')
    data = json.loads(request.data.decode('utf-8'))
    for k in data.keys():
        redisClient.log_debug(k)
    content = base64.b64decode(data['content'])
    style = base64.b64decode(data['style'])
    # resizing logic can live here
    chash = hash_and_send_to_minio('content', content)
    shash = hash_and_send_to_minio('style', style)
    redisClient.client.rpush('requests', chash + ',' + shash)
    redisClient.client.rpush('content', chash)
    redisClient.client.rpush('style', shash)
    redisClient.client.rpush('iterations', data['iterations'])
    redisClient.client.rpush('content-weight', data['content_weight'])
    redisClient.client.rpush('style-weight', data['style_weight'])
    version = redisClient.client.blpop('versions', timeout=0)
    version = version[1].decode('utf-8')

    response = {'content_hash' : chash,
                'style_hash': shash,
                'filename': version,
                'reason': 'Images enqueued for style transfer'}
    redisClient.log_debug(response['content_hash'] + ' and ' + response['style_hash'] + ' ' + response['reason'])
    response_pickled = jsonpickle.encode(response)
    return response_pickled

@app.route('/apiv1/get_image/<string:filename>', methods=['GET'])
def get_image(filename):
    print("In get image endpoint")
    redisClient.log_info('In get image endpoint')
    response = minio_plugin.read_from_minio(filename, redisclient=redisClient)
    return response

@app.route('/', methods=['GET'])
def hello():
    return '<h1> Neural Style Transfer Server</h1><p> Use a valid endpoint </p>'

app.run(host=serverHost, port=serverPort)
