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
parser.add_argument("--db-address", help="Database endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
parser.add_argument("--db-port", help="Database endpoint TCP port, default: 5003", nargs="?", default=5003)
parser.add_argument("--imgmt-address", help="IaaS management endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
parser.add_argument("--imgmt-port", help="IaaS management endpoint TCP port, default: 5004", nargs="?", default=5004)
#parser.add_argument("--repo-address", help="Image repo endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
#parser.add_argument("--repo-port", help="Image repo endpoint TCP port, default: 5006", nargs="?", default=5006)

args = parser.parse_args()

ep_address = args.address
ep_port = args.port
db_address = args.db_address
db_port = args.db_port
iaas_mgmt_address = args.imgmt_address
iaas_mgmt_port = args.imgmt_port
#repo_address = args.repo_address
#repo_port = args.repo_port

### Resource definition

class Test(Resource):
  def get(self):
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class FogApplication(Resource):
  def __init__(self):
    super().__init__()

  def get(self, app_id):
    # determine node id by choosing a node among the ones that implement this app (if any)
    node_dict = requests.get("http://{}:{}/nodes".format(db_address, db_port)).json()
    app_list = requests.get("http://{}:{}/apps".format(db_address, db_port)).json()
    if app_id not in app_list:
      # TODO understand why it returns 200 OK anyway (maybe check the return value(s) of abort)
      return { "message": "Application {} not found.".format(app_id) }, 404
    app = app_list[app_id]
    app_node_list = app["nodes"]

    # TODO IMPORTANT implement a mechanism to avoid sharing apps among different requests
    app_node_list = []

    # check if this app is implemented on some node
    if app_node_list:
      # if we get here, there are active nodes that implement this app
      # pick the first node on the list (TODO implement a better picking method)
      node_id = app_node_list[0]
      node = requests.get("http://{}:{}/node/{}".format(db_address, db_port, node_id)).json()
      node_ip = node["ip"]
      return {"message": "App {} available".format(app_id), "node_id": node_id, "node_ip": node_ip}
    else:
      # this means this app is not implemented/deployed on any node
      # try installing image on a IaaS node to implement this app
      # get list of nodes and pick the first available IaaS nodes having CPU utilization lower than a threshold
      # TODO implement a better picking method
      node_id = ""
      for h_id in node_dict:
        node = node_dict[h_id]
        if node["available"] == "1" and node["class"] == "I":
          for item_id in node["resources"]:
            if node["resources"][item_id]["name"] == "CPU utilization":
              logger.debug("Node {} CPU {}%".format(h_id, node["resources"][item_id]["lastvalue"]))
              if float(node["resources"][item_id]["lastvalue"]) < 90:
                # we have found the node
                node_id = h_id
                break
        if node_id:
          break
      if not node_id:
        return {"message": "App not deployed and no available IaaS node."}, 503
      logger.debug("Chosen node {}".format(node_id))
      node_ip = node["ip"]
      # get list of available images and look for image that offers the required app
      image_list = requests.get("http://{}:{}/images".format(iaas_mgmt_address, iaas_mgmt_port)).json()
      app_image_list = [ image for image in image_list["fogimages"] if app_id in image_list["fogimages"][image]["apps"] ]
      if not app_image_list:
        return {"message": "App not deployed and not provided by any available image."}, 503
      # pick the first image on the list (TODO implement a better picking method)
      image_id = app_image_list[0]
      image_name = image_list["fogimages"][image_id]["name"]
      r = requests.post("http://{}:{}/app/{}".format(iaas_mgmt_address, iaas_mgmt_port, app_id), json={"image_name": image_name, "node_ipv4": node_ip})
      return r.json(), r.status_code
    
  def post(self):
    # retrieve information from POST body
    args = self.parser.parse_args()
    image_id = args["image"]
    # determine node id by choosing a node among the available IaaS nodes (if any)
    node_list = requests.get("http://{}:{}/nodes".format(db_address, db_port, image_id)).json()
    #logger.debug(f"{r}")
    return '', 201

class FogVirtEngine(Resource):
  def __init__(self):
    super().__init__()

  def get(self, fve_id):
    # determine node id by choosing node amons the ones offering this FVE (if any)
    fve_list = requests.get("http://{}:{}/fves".format(db_address, db_port)).json()
    if fve_id not in fve_list:
      # TODO understand why it returns 200 OK anyway (maybe check the return value(s) of abort)
      abort(404, message="Fog Virtualization Engine {} not found.".format(fve_id))
    fve = fve_list[fve_id]
    fve_node_list = fve["nodes"]
    if fve_node_list:
      # there is a node offering this FVE
      # pick the first node on the list (TODO implement a better picking method)
      node_id = fve_node_list[0]
      node = requests.get("http://{}:{}/node/{}".format(db_address, db_port, node_id)).json()
      return {"message": "Fog Virtualization Engine {} available.".format(fve_id), "node_url": node["url"]}
    else:
      return {"message": "FVE {} not available on any node.".format(fve_id)}, 503

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

api.add_resource(FogVirtEngine, '/fve/<fve_id>')

### MAIN

if __name__ == '__main__':

  wait_for_remote_endpoint(db_address, db_port)
  wait_for_remote_endpoint(iaas_mgmt_address, iaas_mgmt_port)
  #wait_for_remote_endpoint(repo_address, repo_port)

  app.run(host=ep_address, port=ep_port, debug=True)

