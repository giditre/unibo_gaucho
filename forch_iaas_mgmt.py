from flask import Flask, request
from flask_restful import Resource, Api, reqparse, abort
import json
import argparse
import requests
import logging
import random
from time import sleep
import os

import docker

### Logging setup

logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

### Resource definition

class Test(Resource):
  def get(self):
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class ImageList(Resource):
  def get(self):
    # TODO get list of allowed images from file and check that they exixt in the repo
    images = {
      "fogimages": {
        "Image01": {
          "name": "alpine",
          "descr": "Lightweight Ubuntu",
          "uri": "alpine",
          "apps": [],
          "sdps": ["SDP002"]
        },
        "Image02": {
          "name": "httpd",
          "descr": "Apache web server",
          "uri": "httpd",
          "apps": ["APP001"],
          "sdps": []
        },
        "Image03": {
          "name": "python3",
          "descr": "Python3 interactive shell",
          "uri": "python",
          "apps": [],
          "sdps": ["SDP001"]
        },
        "Image04": {
          "name": "stress",
          "descr": "Stress",
          "uri": "giditre/gaucho-stress",
          "apps": ["APP002"],
          "sdps": ["SDP003"]
        }
      }
    }

    return images

class FogApplication(Resource):

  def __init__(self):
    super().__init__()
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('image', type=str, help='Image locator')
    self.parser.add_argument('node', type=str, help='Node locator')

  def post(self, app_id):
    ## retrieve information from POST body
    req_json = request.get_json(force=True)
    image_name = req_json["image_name"] 
    node_ipv4 = req_json["node_ipv4"]

    # find image URI based on name
    image_uri = ""
    image_dict = ImageList().get()
    for image_id in image_dict["fogimages"]:
      if image_dict["fogimages"][image_id]["name"] == image_name:
        image_uri = image_dict["fogimages"][image_id]["uri"]
        break
    if not image_uri:
      return {"message": "Aborted: no image found having name {}".format(image_name)}

    try:
      r = requests.post("http://{}:{}/app/{}".format(node_ipv4, 5005, app_id), json={"image_uri": image_uri})
    except requests.exceptions.ConnectionError:
      msg = "Aborted: error in connecting to node {}".format(node_ipv4)
      return {"message": msg}, 500
    resp_json = r.json()
    logger.debug("Response from node {}: {}".format(node_ipv4, resp_json))
    #"0.0.0.0:32774->80/tcp"
    return {
      "message": "Application {} successfully deployed".format(app_id),
      "node_ip": node_ipv4,
      "port_mappings": resp_json["port_mappings"] 
      }, r.status_code

def wait_for_remote_endpoint(ep_address, ep_port, path="test"):
  url = "http://{}:{}/{}".format(ep_address, ep_port, path)
  while True:
    resp_code = -1
    try:
      r = requests.get(url)
      resp_code = r.status_code
    except requests.exceptions.ConnectionError as ce:
      logger.warning("Connection error, retrying soon...")
    if resp_code == 200:
      logger.info("Remote endpoint ({}) ready".format(url))
      break
    logger.warning("Remote endpoint ({}) not ready (reponse code {}), retrying soon...".format(url, resp_code))
    sleep(random.randint(5,15))

### MAIN

if __name__ == '__main__':

  ### Command line argument parsing
  
  parser = argparse.ArgumentParser()
  
  parser.add_argument("address", help="Endpoint IP address")
  parser.add_argument("port", help="Endpoint TCP port")
  parser.add_argument("-w", "--wait-remote", help="Wait for remote endpoint(s), default: false", action="store_true", default=False)
  parser.add_argument("-d", "--debug", help="Run in debug mode, default: false", action="store_true", default=False)
  
  args = parser.parse_args()
  
  ep_address = args.address
  ep_port = args.port
  wait_remote = args.wait_remote
  debug = args.debug

  ### API definition
  
  app = Flask(__name__)
  api = Api(app)
  
  api.add_resource(Test, "/test")
  api.add_resource(ImageList, "/images")
  api.add_resource(FogApplication, "/app/<app_id>")

  app.run(host=ep_address, port=ep_port, debug=debug)

