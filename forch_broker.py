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
      return { "message": "Application {} not defined".format(app_id) }, 404
    app = app_list[app_id]
    app_node_list = app["nodes"]

    # TODO IMPORTANT implement a mechanism to avoid sharing apps among different requests
    #app_node_list = []

    # check if this app is implemented on some node
    if app_node_list:
      # if we get here, there are active nodes that implement this app
      # check if any of those has resource usage lower than a threshold
      node_id = ""
      candidate_node_list = []
      for h_id in app_node_list:
        node = node_dict[h_id]
        if node["available"] == "1" and node["class"] == "S":
          for item_id in node["resources"]:
            if node["resources"][item_id]["name"] == "CPU utilization":
              logger.debug("Node {} CPU {}%".format(h_id, node["resources"][item_id]["lastvalue"]))
              if float(node["resources"][item_id]["lastvalue"]) < 90:
                # we have found a candidate node
                candidate_node_list.append(h_id)

      if candidate_node_list:
        # TODO implement heuristic picking method
        node_id = candidate_node_list[0]
        logger.debug("Picked node {}".format(node_id))

      if node_id:
        node = requests.get("http://{}:{}/node/{}".format(db_address, db_port, node_id)).json()
        node_ip = node["ip"]
        r = requests.post("http://{}:{}/app/{}".format(node_ip, 5005, app_id), json={"test": "dummy"})
        resp_json = r.json()
        port = resp_json["port"]
        #return {"message": "App {} allocated".format(app_id), "node_class": "S", "node_id": node_id, "node_ip": node_ip, "service_port": port}
        return {"message": "APP {} allocated".format(app_id), "node_class": "S", "node_id": node_id, "service_port": port}
      else:
        logger.debug("Application not already available on any SaaS node")

    # getting here means this app is not implemented/deployed on any node
    logger.debug("Application not deployed on any node")
    # try installing image on a IaaS node to implement this app
    # get list of nodes and pick the first available IaaS nodes having CPU utilization lower than a threshold
    # TODO implement a better picking method
    node_id = ""
    candidate_node_list = []
    for h_id in node_dict:
      node = node_dict[h_id]
      if node["available"] == "1" and node["class"] == "I":
        for item_id in node["resources"]:
          if node["resources"][item_id]["name"] == "CPU utilization":
            logger.debug("Node {} CPU {}%".format(h_id, node["resources"][item_id]["lastvalue"]))
            if float(node["resources"][item_id]["lastvalue"]) < 90:
              # we have found a candidate node
              candidate_node_list.append(h_id)

    if candidate_node_list:
      # TODO implement heuristic picking method
      node_id = candidate_node_list[0]
      logger.debug("Picked node {}".format(node_id))

    if not node_id:
      return {"message": "Application {} not deployed and no available IaaS node".format(app_id)}, 503

    node = node_dict[node_id]
    logger.debug("Chosen node: {}".format(node_id, node))
    node_ip = node["ip"]
    # get list of available images and look for image that offers the required app
    image_list = requests.get("http://{}:{}/images".format(iaas_mgmt_address, iaas_mgmt_port)).json()
    app_image_list = [ image for image in image_list["fogimages"] if app_id in image_list["fogimages"][image]["apps"] ]
    if not app_image_list:
      return {"message": "Application not deployed and not provided by any available image."}, 503
    # pick the first image on the list (TODO implement a better picking method)
    image_id = app_image_list[0]
    image_name = image_list["fogimages"][image_id]["name"]
    r = requests.post("http://{}:{}/app/{}".format(iaas_mgmt_address, iaas_mgmt_port, app_id), json={"image_name": image_name, "node_ipv4": node_ip})
    if r.status_code == 201:
      r_json = r.json()
      # "0.0.0.0:32809->5100/tcp"
      port = r_json["port_mappings"][0].split(":")[1].split("-")[0]
      #resp_json = {"message": "App {} allocated".format(app_id), "node_class": "I", "node_id": node_id, "node_ip": node_ip, "service_port": port}
      resp_json = {"message": "App {} allocated".format(app_id), "node_class": "I", "node_id": node_id, "service_port": port}
      return resp_json, 201
    else:
      return r.json(), r.status_code
    
  #def post(self):
  #  # retrieve information from POST body
  #  args = self.parser.parse_args()
  #  image_id = args["image"]
  #  # determine node id by choosing a node among the available IaaS nodes (if any)
  #  node_list = requests.get("http://{}:{}/nodes".format(db_address, db_port, image_id)).json()
  #  #logger.debug(f"{r}")
  #  return '', 201

class SoftDevPlatform(Resource):
  def __init__(self):
    super().__init__()

  def get(self, sdp_id):
    # determine node id by choosing node among the ones offering this SDP (if any)
    node_dict = requests.get("http://{}:{}/nodes".format(db_address, db_port)).json()
    sdp_list = requests.get("http://{}:{}/sdps".format(db_address, db_port)).json()
    if sdp_id not in sdp_list:
      return { "message": "SDP {} not found".format(sdp_id) }, 404
    sdp = sdp_list[sdp_id]
    sdp_node_list = sdp["nodes"]
    if sdp_node_list:
      # if we get here, there are active nodes that offer this SDP
      # check if any of those has resource usage lower than a threshold
      node_id = ""
      candidate_node_list = []
      for h_id in sdp_node_list:
        node = node_dict[h_id]
        if node["available"] == "1" and node["class"] == "P":
          for item_id in node["resources"]:
            if node["resources"][item_id]["name"] == "CPU utilization":
              logger.debug("Node {} CPU {}%".format(h_id, node["resources"][item_id]["lastvalue"]))
              if float(node["resources"][item_id]["lastvalue"]) < 90:
                # we have found a candidate node
                candidate_node_list.append(h_id)

      if candidate_node_list:
        # TODO implement heuristic picking method
        node_id = candidate_node_list[0]
        logger.debug("Picked node {}".format(node_id))
        node = requests.get("http://{}:{}/node/{}".format(db_address, db_port, node_id)).json()
        node_ip = node["ip"]
        r = requests.post("http://{}:{}/sdp/{}".format(node_ip, 5005, sdp_id), json={"test": "dummy"})
        resp_json = r.json()
        port = resp_json["port"]
        #return {"message": "SDP {} allocated".format(sdp_id), "node_class": "P", "node_id": node_id, "node_ip": node_ip, "service_port": port}
        return {"message": "SDP {} allocated".format(sdp_id), "node_class": "P", "node_id": node_id, "service_port": port}
      #else:
      #  return {"message": "SDP {} is deployed but no available PaaS node".format(sdp_id)}, 503
    else:
      # getting here means this SDP is not implemented/deployed on any node
      logger.debug("SDP currently not deployed on any node")
      # try installing image on a IaaS node to implement this SDP
      # get list of nodes and pick the first available IaaS nodes having CPU utilization lower than a threshold
      # TODO implement a better picking method
      node_id = ""
      candidate_node_list = []
      for h_id in node_dict:
        node = node_dict[h_id]
        if node["available"] == "1" and node["class"] == "I":
          for item_id in node["resources"]:
            if node["resources"][item_id]["name"] == "CPU utilization":
              logger.debug("Node {} CPU {}%".format(h_id, node["resources"][item_id]["lastvalue"]))
              if float(node["resources"][item_id]["lastvalue"]) < 90:
                # we have found a candidate node
                candidate_node_list.append(h_id)

      if candidate_node_list:
        # TODO implement heuristic picking method
        node_id = candidate_node_list[0]
        logger.debug("Picked node {}".format(node_id))

      if not node_id:
        return {"message": "SDP {} not deployed and no available IaaS node".format(sdp_id)}, 503

      node = node_dict[node_id]
      logger.debug("Chosen node: {}".format(node_id, node))
      node_ip = node["ip"]
      # get list of available images and look for image that offers the required SDP
      image_list = requests.get("http://{}:{}/images".format(iaas_mgmt_address, iaas_mgmt_port)).json()
      sdp_image_list = [ image for image in image_list["fogimages"] if sdp_id in image_list["fogimages"][image]["sdps"] ]
      if not sdp_image_list:
        return {"message": "SDP {} not deployed and not provided by any available image".format(sdp_id)}, 503
      # pick the first image on the list (TODO implement a better picking method)
      image_id = sdp_image_list[0]
      image_name = image_list["fogimages"][image_id]["name"]
      r = requests.post("http://{}:{}/sdp/{}".format(iaas_mgmt_address, iaas_mgmt_port, sdp_id), json={"image_name": image_name, "node_ipv4": node_ip})
      if r.status_code == 201:
        r_json = r.json()
        # "0.0.0.0:32809->5100/tcp"
        port = r_json["port_mappings"][0].split(":")[1].split("-")[0]
        #resp_json = {"message": "SDP {} allocated".format(sdp_id), "node_class": "I", "node_id": node_id, "node_ip": node_ip, "service_port": port}
        resp_json = {"message": "SDP {} allocated".format(sdp_id), "node_class": "I", "node_id": node_id, "service_port": port}
        return resp_json, 201
      else:
        return r.json(), r.status_code

class FogVirtEngine(Resource):
  def __init__(self):
    super().__init__()

  def get(self, fve_id):
    # determine node id by choosing node among the ones offering this FVE (if any)
    node_dict = requests.get("http://{}:{}/nodes".format(db_address, db_port)).json()
    fve_list = requests.get("http://{}:{}/fves".format(db_address, db_port)).json()
    if fve_id not in fve_list:
      return { "message": "FVE {} not found".format(fve_id) }, 404
    fve = fve_list[fve_id]
    fve_node_list = fve["nodes"]
    if fve_node_list:
      # if we get here, there are active nodes that offer this FVE
      # check if any of those has resource usage lower than a threshold
      node_id = ""
      candidate_node_list = []
      for h_id in fve_node_list:
        node = node_dict[h_id]
        if node["available"] == "1" and node["class"] == "P":
          for item_id in node["resources"]:
            if node["resources"][item_id]["name"] == "CPU utilization":
              logger.debug("Node {} CPU {}%".format(h_id, node["resources"][item_id]["lastvalue"]))
              if float(node["resources"][item_id]["lastvalue"]) < 90:
                # we have found a candidate node
                candidate_node_list.append(h_id)

      if candidate_node_list:
        # TODO implement heuristic picking method
        node_id = candidate_node_list[0]
        logger.debug("Picked node {}".format(node_id))
        node = requests.get("http://{}:{}/node/{}".format(db_address, db_port, node_id)).json()
        node_ip = node["ip"]
        logger.debug("FVE {} available at {}".format(fve_id, node_ip))
        r = requests.post("http://{}:{}/fve/{}".format(node_ip, 5005, fve_id), json={"test": "dummy"})
        resp_json = r.json()
        port = resp_json["port"]
        #return {"message": "FVE {} allocated".format(fve_id), "node_class": "I", "node_id": node_id, "node_ip": node_ip, "service_port": port}
        return {"message": "FVE {} allocated".format(fve_id), "node_class": "I", "node_id": node_id, "service_port": port}
      else:
        return {"message": "FVE {} is deployed but no available IaaS node".format(fve_id)}, 503
    else:
      return {"message": "FVE {} not deployed".format(fve_id)}, 503

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
  parser.add_argument("--db-address", help="Database endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
  parser.add_argument("--db-port", help="Database endpoint TCP port, default: 5003", nargs="?", default=5003)
  parser.add_argument("--imgmt-address", help="IaaS management endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
  parser.add_argument("--imgmt-port", help="IaaS management endpoint TCP port, default: 5004", nargs="?", default=5004)
  parser.add_argument("-w", "--wait-remote", help="Wait for remote endpoint(s), default: false", action="store_true", default=False)
  parser.add_argument("-d", "--debug", help="Run in debug mode, default: false", action="store_true", default=False)
  
  args = parser.parse_args()
  
  ep_address = args.address
  ep_port = args.port
  db_address = args.db_address
  db_port = args.db_port
  iaas_mgmt_address = args.imgmt_address
  iaas_mgmt_port = args.imgmt_port
  wait_remote = args.wait_remote
  debug = args.debug

  if wait_remote:
    wait_for_remote_endpoint(db_address, db_port)
    wait_for_remote_endpoint(iaas_mgmt_address, iaas_mgmt_port)

  ### API definition
  
  app = Flask(__name__)
  api = Api(app)
  
  api.add_resource(Test, '/test')
  api.add_resource(FogApplication, '/app/<app_id>')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

  app.run(host=ep_address, port=ep_port, debug=debug)

