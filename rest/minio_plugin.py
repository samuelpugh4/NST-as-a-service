from minio import Minio
import os
import sys
import base64
import io
import time

minioHost = os.getenv("MINIO_HOST") or "localhost"
minioPort = os.getenv("MINIO_PORT") or "9000"
minioUser = os.getenv("MINIO_USER") or "rootuser"
minioPasswd = os.getenv("MINIO_PASSWD") or "rootpass123"
minioHostPort = minioHost + ":" + minioPort

client = Minio(minioHostPort,
               secure=False,
               access_key=minioUser,
               secret_key=minioPasswd)

def dump_to_minio(payload, redisclient):
    bucketname = payload['bucket']
    if not client.bucket_exists(bucketname):
        redisclient.log_info(f"Create bucket {bucketname}")
        client.make_bucket(bucketname)

    buckets = client.list_buckets()

    for bucket in buckets:
        redisclient.log_info(f"Bucket {bucket.name}, created {bucket.creation_date}")
        
    counter = 0
    try:
        redisclient.log_info(f"Objects in {bucketname} are originally: ")
        for thing in client.list_objects(bucketname, recursive=True):
            counter += 1
            redisclient.log_info(thing.object_name)
        assert counter != 0
    except AssertionError:
        redisclient.log_debug(f"{bucketname} is empty")
    
    try:
        redisclient.log_info(f"Add file {payload['digest']} as object {payload['digest']}")
        bytes_to_put = io.BytesIO(payload['bytes'])
        client.put_object(bucketname, payload['digest'], bytes_to_put, length=len(payload['bytes']))
    except Exception as err:
        redisclient.log_debug("Error when adding files the first time")
        redisclient.log_debug(err)

    redisclient.log_info(f"Objects in {bucketname} are now:")
    for thing in client.list_objects(bucketname, recursive=True):
        redisclient.log_info(thing.object_name)

    sys.stdout.flush()
    time.sleep(3)

def read_from_minio(filename, redisclient):
    bucketname = 'output'
    buckets = client.list_buckets()
    bucket = None
    for b in buckets:
        if b.name == bucketname:
            bucket = b
    try:
        assert bucket is not None

    except AssertionError:
        err = 'Output bucket does not yet exist, wait for the style transfer to complete.'
        redisclient.log_debug(err)
        return {'error': err}
    image_string = '{}'.format(filename)
    cwd = os.getcwd()
    try:
        for thing in client.list_objects(bucketname, recursive=True):
            if thing.object_name == image_string:
                client.fget_object(bucketname, thing.object_name, cwd + "/{}".format(image_string))
                redisclient.log_info('Object {} acquired'.format(thing.object_name))
                btz = base64.b64encode( open(cwd+'/{}'.format(image_string), "rb").read() ).decode('utf-8')
                os.remove(cwd+'/{}'.format(image_string))
                return {image_string: btz}

    except Exception as err:
        redisclient.log_debug(err.message)
        return {'error': err.message}

    return {'error': 'file {} not found in bucket'.format(filename)}