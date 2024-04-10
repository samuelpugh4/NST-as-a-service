#!/usr/bin/env python3

import requests
import json, jsonpickle
import os
import sys
import time
import base64
import glob
from argparse import ArgumentParser

REST = os.getenv("REST") or "35.193.135.26" # GKE ip address

##
# The following routine makes a JSON REST query of the specified type
# and if a successful JSON reply is made, it pretty-prints the reply
##

def mkReq(reqmethod, endpoint, data, verbose=True, return_response=False):
    if verbose:
        print(f"Response to http://{REST}/{endpoint} request is {type(data)}")
    jsonData = jsonpickle.encode(data)
    if verbose and data != None:
        print(f"Make request http://{REST}/{endpoint} with json {data.keys()}")
    response = reqmethod(f"http://{REST}/{endpoint}", data=jsonData,
                         headers={'Content-type': 'application/json'})
    if response.status_code == 200:
        jsonResponse = json.dumps(response.json(), indent=4, sort_keys=True)
        if return_response:
            return response.json()
        else:
            if verbose:
                print(jsonResponse)
            return
    else:
        if verbose:
            print(
                f"response code is {response.status_code}, raw response is {response.text}")
        return response.text

def style_transfer(args):
    cwd = os.getcwd()
    content_image = cwd + '/' + args.content
    style_image = cwd + '/' + args.style
    resp = mkReq(requests.post, "apiv1/style_transfer/",
            data={
                "content": base64.b64encode( open(content_image, "rb").read() ).decode('utf-8'),
                "style": base64.b64encode( open(style_image, "rb").read() ).decode('utf-8'),
                "iterations": args.iterations,
                "content_weight": args.content_weight,
                "style_weight": args.style_weight,
                "callback": {
                    "url": "http://{REST}",
                    "data": {"content": args.content,
                            "style": args.style,
                            "iterations": args.iterations,
                            "content_weight": args.content_weight,
                            "style_weight": args.style_weight,
                            "data": "to be returned"}
                }
            },
            verbose=True, 
            return_response=True
            )
    if args.save_names:
        with open('submitted_image_names.txt', 'a') as f:
            try:
                filename = resp['filename'].split('.png')[0]
                f.write(filename)
                f.write('\n')
            except TypeError:
                print('Server side error')

def get_images():
    with open('submitted_image_names.txt', 'r') as f:
        filenames = f.readlines()
    print(filenames)
    successful_gets = []
    for filename in filenames:
        filename = filename.strip('\n')
        resp = mkReq(
            requests.get, "apiv1/get_image/{}".format(filename), 
            data={"callback": {
                    "url": "http://{REST}",
                    "data": "to be returned"
                    }
                }, 
            verbose=True, return_response=True
        )
        if resp.get('error') is None:
            # we got the bytes
            print('got the bytes')
            image_f = open('{}.png'.format(filename), 'wb')
            image = base64.b64decode(resp[filename])
            image_f.write(image)
            successful_gets.append(filename)
            image_f.close()
        else:
            print(resp['error'])
    
    print(successful_gets)
    with open('submitted_image_names.txt', 'r') as f:
        lines = f.readlines()

    with open('submitted_image_names.txt', 'w') as f:
        print(lines)
        for line in lines:
            line = line.strip('\n')
            if line not in successful_gets:
                f.write(line + '\n')


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--save_names', action='store_true')
    parser.add_argument('--do_style_transfer', action='store_true')
    parser.add_argument('--content', '-c', type=str,  help='Relative path to content image')
    parser.add_argument('--style', '-s', type=str,  help='Relative path to style image')
    parser.add_argument('--iterations', '-i', type=int,  help='Model iterations')
    parser.add_argument('--local_save', '-ls',  action='store_true')
    parser.add_argument('--content_weight', '-cw', type=float, default=5.0, help='Model content weight', )
    parser.add_argument('--style_weight', '-sw', type=float, default=500.0, help='Model style weight')
    args = parser.parse_args()
    if args.do_style_transfer:
        style_transfer(args)
    if args.local_save:
        get_images()
