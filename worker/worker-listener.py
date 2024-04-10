import os
import redis
import sys
import time

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

def field_request():
    output_image = None
    try:
        output_image = redisClient.client.blpop('output', timeout=0)
    except Exception as err:
        redisClient.log_debug(err.message)
    if output_image is not None:
        return output_image[1].decode('utf-8')
    else:
        redisClient.log_debug('AHHHHH in output fielding')
        return output_image

while True:
    redisClient.log_info('listening for output')
    req = field_request()
    if req is not None:
        redisClient.log_info(req)
        path = req
        if os.path.exists(path):
            succeeded = minio_plugin.dump_output_image_to_minio(path, redisClient)
            if succeeded:
                redisClient.log_debug('Successfully uploaded {} to minio'.format(req))
        else:
            redisClient.log_info('Output does not yet exist, returning {} to output queue and continuing to listen'.format(req))
            redisClient.client.rpush('output', req)
            time.sleep(30)
