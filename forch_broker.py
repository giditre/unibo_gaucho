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
parser.add_argument("--db-address", help="Database endpoint IP address", nargs="?", default="127.0.0.1")
parser.add_argument("--db-port", help="Database endpoint TCP port", nargs="?", default=5003)
parser.add_argument("--imgmt-address", help="IaaS management endpoint IP address", nargs="?", default="127.0.0.1")
parser.add_argument("--imgmt-port", help="IaaS management endpoint TCP port", nargs="?", default=5004)
parser.add_argument("--repo-address", help="Image repo endpoint IP address", nargs="?", default="127.0.0.1")
parser.add_argument("--repo-port", help="Image repo endpoint TCP port", nargs="?", default=5006)

args = parser.parse_args()

ep_address = args.address
ep_port = args.port
db_address = args.db_address
db_port = args.db_port
iaas_mgmt_address = args.imgmt_address
iaas_mgmt_port = args.imgmt_port
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

  def get(self, app_id):
    # determine node id by choosing a node among the ones that implement this app (if any)
    app_list = requests.get("http://{}:{}/apps".format(db_address, db_port)).json()
    if app_id not in app_list:
      # TODO understand why it returns 200 OK anyway (maybe check the return value(s) of abort)
      abort(404, message="Application {} not found.".format(app_id))
    app = app_list[app_id]
    app_node_list = app["nodes"]
    # check if this app is implemented on some node
    if app_node_list:
      # if we get here, there are active nodes that implement this app
      # pick the first node on the list (TODO implement a better picking method)
      node_id = app_node_list[0]
      node = requests.get("http://{}:{}/node/{}".format(db_address, db_port, node_id)).json()
      return {"message": "Application {} available".format(app_id), "node_url": node["url"]}
    else:
      # this means this app is not implemented/deployed on any node
      # TODO try installing image on a IaaS node to implement this app
      # get list of nodes and look for IaaS nodes
      node_list = requests.get("http://{}:{}/nodes".format(db_address, db_port)).json()
      iaas_nodes = [ node for node in node_list if node_list[node]["class"] == "I" ]    # TODO also check if node has resources available
      if not iaas_nodes:
        return "App not deployed and no available IaaS node", 503
      # pick the first node on the list (TODO implement a better picking method)
      node_id = iaas_nodes[0]
      node_url = node_list[node_id]["url"]
      # get list of available images and look for image that offers the required app
      image_list = requests.get("http://{}:{}/images".format(iaas_mgmt_address, iaas_mgmt_port)).json()
      app_image_list = [ image for image in image_list["fogimages"] if app_id in image_list["fogimages"][image]["apps"] ]
      if not app_image_list:
        return "App not deployed and not provided by any available image", 503
      # pick the first image on the list (TODO implement a better picking method)
      image_id = app_image_list[0]
      image_uri = image_list["fogimages"][image_id]["uri"]
      logger.debug(image_uri) 
      logger.debug(node_url) 
      r = requests.post("http://{}:{}/app".format(iaas_mgmt_address, iaas_mgmt_port), json={"image_uri": image_uri, "node_url": node_url})
      return r.json(), r.status_code
    
  def post(self):
    # retrieve information from POST body
    args = self.parser.parse_args()
    image_id = args["image"]
    # determine node id by choosing a node among the available IaaS nodes (if any)
    node_list = requests.get("http://{}:{}/nodes".format(db_address, db_port, image_id)).json()
    #logger.debug(f"{r}")
    return '', 201

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

### API definition

app = Flask(__name__)
api = Api(app)

api.add_resource(Test, '/test')

api.add_resource(FogApplication, '/app/<app_id>')

### MAIN

if __name__ == '__main__':

  wait_for_remote_endpoint(db_address, db_port)
  wait_for_remote_endpoint(iaas_mgmt_address, iaas_mgmt_port)
  wait_for_remote_endpoint(repo_address, repo_port)

  app.run(host=ep_address, port=ep_port, debug=True)

