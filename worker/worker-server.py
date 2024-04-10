import os
import redis
import sys
import time
import math
from PIL import Image

import minio_plugin


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

def field_request(queue, timeout=0):
    try:
        res = redisClient.client.blpop(queue, timeout=timeout)
    except Exception as err:
        redisClient.log_debug(err.message)
    if res is not None:
        redisClient.log_info('{} popped from {} queue'.format(res, queue))
        return res[1].decode('utf-8')
    else:
        redisClient.log_debug('AHHHHH')
        return res


def generate_output_filename(content, style, version_string):
    redisClient.log_info('Generating filename from content and style hashes')
    return '{}_in_the_style_of_{}_{}.png'.format(content, style, version_string)


def check_and_resize_image(filename, max_size=200000):
    img = Image.open(filename)
    old_size = img.size
    w, h = old_size
    while w * h > max_size:
        w = w * 0.999
        h = h * 0.999
    w = math.floor(w)
    h = math.floor(h)
    new_size = (w, h)
    img = img.resize(new_size)
    img.save(filename)
    return (old_size, new_size)


def hydrate_image(queue, req_hash):   
    try:
        hash = redisClient.client.blpop(queue, timeout=0)
    except Exception as err:
        redisClient.log_debug(err.message)
    
    if hash is not None:
        hash = hash[1].decode('utf-8')
        try:
            assert hash == req_hash
        except AssertionError:
            redisClient.log_debug('Hash mismatch between request and content queue')
            redisClient.log_debug(hash)
            redisClient.log_debug(req_hash)
            return None
        redisClient.log_info('Hydrating image from {} queue...'.format(queue))  
        redisClient.log_info('{} popped from {} queue'.format(hash, queue))
        # save the image locally so nst can pick it up
        filename = minio_plugin.save_image_locally(hash, queue, redisClient, path='/srv/')
        # check and resize
        old_dims, new_dims = check_and_resize_image(filename)
        if old_dims != new_dims:
            redisClient.log_info('{} image resized from {} to {}'.format(queue, old_dims, new_dims))
    else:
        filename = None
    return filename

os.system('python worker-listener.py &')
all_seen_pairs = {}
while True:
    redisClient.log_info('Waiting for work')
    req = field_request('requests')
    hashes = req.split(',')
    redis_image_queues = ['content', 'style']
    filenames = {'content': None, 
                'style': None}
    for hash in hashes:
        redisClient.log_debug(hash)
    for hash,queue in list(zip(hashes,redis_image_queues)):
        filename = hydrate_image(queue, hash)
        filenames[queue] = filename
    iterations = field_request('iterations')
    if iterations is None:
        iterations = 10  # default 
    content_weight = field_request('content-weight', timeout=1)
    style_weight = field_request('style-weight', timeout=1)

    good=True
    for queue,filename in filenames.items():
        if filename is None:
            redisClient.log_debug('Invalid {} option'.format(queue))
            good=False
    
    if good:
        if all_seen_pairs.get(req) is None:
            all_seen_pairs[req] = 1
        else:
            all_seen_pairs[req] += 1
        redisClient.log_debug(req)
        redisClient.log_debug(all_seen_pairs[req])
        version_string = 'v{}'.format(all_seen_pairs[req])
        filenames['output'] = generate_output_filename(hashes[0], hashes[1], version_string)
        redisClient.client.rpush('versions', filenames['output'])
        redisClient.log_info('Generating art from {} and {} over {} iterations'.format(
            filenames['content'],
            filenames['style'], 
            iterations)
            )
        final_param = ''
        if content_weight is not None:
            final_param = final_param + '--content-weight {} '.format(content_weight)
        if style_weight is not None:
            final_param = final_param + '--style-weight {}'.format(style_weight)
        os.system('python neural_style.py --content {} --styles {} --output {} --iterations {} {} &'.format(
            filenames['content'],
            filenames['style'],
            '/srv/'+filenames['output'],
            iterations, 
            final_param)
        )
        redisClient.client.lpush('output', '/srv/'+filenames['output'])
