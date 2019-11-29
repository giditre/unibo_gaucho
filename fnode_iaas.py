from flask import Flask, request
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
parser.add_argument("--repo-address", help="Image repo endpoint IP address", nargs="?", default="127.0.0.1")
parser.add_argument("--repo-port", help="Image repo endpoint TCP port", nargs="?", default=5006)

args = parser.parse_args()

ep_address = args.address
ep_port = args.port
repo_address = args.repo_address
repo_port = args.repo_port

### Resource definition

class Test(Resource):
  def get(self):
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class FogApplication(Resource):
  def __init__(self):
    super().__init__()
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('image', type=str, help='Image locator')
  def post(self):
    ## retrieve information from POST body
    #args = self.parser.parse_args()
    #image_id = args["image"]
    image_uri = request.get_json(force=True)["uri"]
    logger.debug(f"{image_uri}")
    r = requests.get("http://{}:{}/image/{}".format(repo_address, repo_port, image_uri)).json()
    logger.debug(f"{r}")
    return '', 201

def wait_for_remote_endpoint(ep_address, ep_port):
  while True:
    resp_code = -1
    try:
      r = requests.get("http://{}:{}/test".format(ep_address, ep_port))
      resp_code = r.status_code
    except requests.exceptions.ConnectionError as ce:
      logger.warning("Connection error, retrying soon...")
    if resp_code == 200:
      logger.info("Remote endpoint ready")
      break
    logger.warning("Remote endpoint not ready (reponse code {}), retrying soon...".format(resp_code))
    sleep(random.randint(5,15))

### API definition

app = Flask(__name__)
api = Api(app)

api.add_resource(Test, '/test')

api.add_resource(FogApplication, '/app')

### MAIN

if __name__ == '__main__':

  wait_for_remote_endpoint(repo_address, repo_port)

  app.run(host=ep_address, port=ep_port, debug=True)

