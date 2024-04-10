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

def dump_output_image_to_minio(image_filepath, redisclient):
    bucketname='output'
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
        redisclient.log_debug(f"{bucketname} is empty, adding first item...")
    status = True
    try:
        image_name = image_filepath.split('.png')[0].split('/')[-1]
        client.fput_object(bucketname, image_name, image_filepath, content_type='image/png')
        redisclient.log_info(f"Add file {image_name} as object {image_name}")
    except Exception as err:
        redisclient.log_debug("Error when adding output image")
        redisclient.log_debug(err)
        status = False

    redisclient.log_info(f"Objects in {bucketname} are now:")
    for thing in client.list_objects(bucketname, recursive=True):
        redisclient.log_info(thing.object_name)
    
    sys.stdout.flush()
    return status

def save_image_locally(hash, queue, redisclient, path):
    bucketname=queue
    if not client.bucket_exists(bucketname):
        redisclient.log_info(f"Bucket {bucketname} does not exist")
        return None
   
    redisclient.log_debug('In local save')

    try:
        for thing in client.list_objects(bucketname, recursive=True):
            if thing.object_name == hash:
                redisclient.log_debug('Found {} object in {}'.format(hash, queue))
                retries = 5
                max_retries = 5
                while retries > 0:
                    try:
                        filename = path + "{}-{}-image.png".format(hash, queue)
                        redisclient.log_debug(filename)
                        client.fget_object(bucketname, thing.object_name, filename)
                        assert os.path.exists(filename), "Saving failed, retrying {}/{}...".format(retries, max_retries)
                        redisclient.log_info('Object {} saved to {}'.format(thing.object_name, filename))
                        return filename
                    except AssertionError as err:
                        redisclient.log_debug(err.message)
                        retries -= 1
                redisclient.log_debug('Error with local save')
                return None
    except Exception as err:
        redisclient.log_debug(err.message)
        return None
