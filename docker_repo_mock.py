from flask import Flask
from flask_restful import Resource, Api, reqparse, abort
import json
import argparse
import requests
import logging
import random
from time import sleep
import os

### Logging setup

logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

### Command line argument parsing

parser = argparse.ArgumentParser()

parser.add_argument("address", help="Endpoint IP address")
parser.add_argument("port", help="Endpoint TCP port")

args = parser.parse_args()

ep_address = args.address
ep_port = args.port

### global variables

image_list = {
  img : {
    "name": img,
    "descr": f"Description of image {img}",
    "uri": f"fogimages/{img}",
    "apps": [ f"FA{n:03d}" ]
  } for n, img in zip([ n for n in range(1,11) ], [ f"Image{n:02d}" for n in range(1,11) ])
}

### Resource definition

class Test(Resource):
  def get(self):
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class ImageList(Resource):
  def get(self):
    return image_list

class Image(Resource):
  def get(self, image_id):
    return image_list[image_id]

### API definition

app = Flask(__name__)
api = Api(app)

api.add_resource(Test, '/test')

api.add_resource(ImageList, '/images')
api.add_resource(Image, '/image/<image_id>')


### MAIN

if __name__ == '__main__':

  app.run(host=ep_address, port=ep_port, debug=True)

