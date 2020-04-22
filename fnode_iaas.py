from flask import Flask, request
from flask_restful import Resource, Api, reqparse, abort
import json
import argparse
import requests
import logging
import random
from time import sleep
import datetime
import os
import threading
from collections import Counter

import docker

import fnode_agent as fnagent

### Docker

docker_client = docker.from_env()

### Resource definition

class Test(Resource):
  def get(self):
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class FogNodeInfo(Resource):
  def get(self):
    return {"class": "I"}

class FogApplicationList(Resource):
  def get(self):
    app_counter = Counter([ cont.name.split("_")[0] for cont in docker_client.containers.list() if cont.name.startswith("APP")])
    return {"apps": dict(app_counter)}
      
  def delete(self):
    for cont in docker_client.containers.list():
      if cont.name.startswith("APP"):
        cont.stop()
    resp = docker_client.containers.prune()
    return {"message": resp}, 200

class FogApplication(Resource):

  def post(self, app_id):
    # retrieve information from POST body
    req_json = request.get_json(force=True)
    
    image_uri = ""
    if "image_uri" in req_json:
      image_uri = req_json["image_uri"]
    else:
      # TODO: GET the image by app_id from forch_iaas_mgmt
      pass

    command = ""
    if "command" in req_json:
      command = req_json["command"]

    entrypoint = ""
    if "entrypoint" in req_json:
      entrypoint = req_json["entrypoint"]

    # here try to deploy image image_uri on this node

    # check if image is present on this node. If not, TODO check if image is allowed. Is yes, pull it from repo.
    
    if not docker_client.images.list(name=image_uri):
      logger.debug("Image {} not found on this node, pulling it...".format(image_uri))
      docker_client.images.pull(image_uri, tag="latest")
    
    cont_name = app_id + "_" + image_uri.replace("/", "-").replace(":", "-") + "_" + '{0:%Y%m%d-%H%M%S-%f}'.format(datetime.datetime.now())

    ## TODO IMPORTANT find a smarter way to implement command to stress
    #if image_uri == "progrium/stress":
    #  #command = "stress --cpu 1 --io 1 --vm 1 --vm-bytes 1G --timeout 36000s"
    #  command = "stress --cpu 1 --timeout 36000s"

    logger.debug("Deploying app {} in container {} with image {}{}".format(app_id,
      cont_name,
      image_uri,
      " and command '{}'".format(command) if command else ""
      )
    )

    try:
      docker_client.containers.run(image_uri, name=cont_name, detach=True, stdin_open=True, tty=True, publish_all_ports=True, restart_policy={"Name": "on-failure", "MaximumRetryCount": 3}, command=command, entrypoint=entrypoint)
    except docker.errors.ImageNotFound as e:
      return {"message": str(e)}, 404

    #with open("/tmp/{}.json".format(cont_name), "w") as f:
    #  json.dump({"image": image_uri, "app": app_id}, f)

    container = docker_client.containers.get(cont_name)

    cont_ip = container.attrs["NetworkSettings"]["IPAddress"]
    logger.debug(cont_ip)

    port_mappings = []

    ports_dict = container.attrs["NetworkSettings"]["Ports"]
    for cont_port in ports_dict:
      for host_port_dict in ports_dict[cont_port]:
        port_map = "{}:{}->{}".format(host_port_dict["HostIp"], host_port_dict["HostPort"], cont_port)
        port_mappings.append(port_map)
        logger.debug(port_map)

    return {"message": "Deployed image {}".format(image_uri),
        "name": cont_name,
        "cont_ip": cont_ip,
        "port_mappings": port_mappings
        }, 201

class FogVirtEngineList(Resource):

  def get(self):
    # TODO do it not hardcoded
    return {"fves": {"FVE001": 1}}

  def delete(self):
    for cont in docker_client.containers.list():
      if cont.name.startswith("FVE"):
        cont.stop()
    resp = docker_client.containers.prune()
    return {"message": resp}, 200


class FogVirtEngine(Resource):

  def get(self):
    # TODO do it not hardcoded
    return {"message": "OK"}

  def post(self, fve_id):
    # retrieve information from POST body
    req_json = request.get_json(force=True)
    
    image_uri = ""
    if "image_uri" in req_json:
      image_uri = req_json["image_uri"]
    else:
      return {"message": "Image URI not specified"}, 400

    command = ""
    if "command" in req_json:
      command = req_json["command"]

    entrypoint = ""
    if "entrypoint" in req_json:
      entrypoint = req_json["entrypoint"]

    # here try to deploy image image_uri on this node

    # check if image is present on this node. If not, TODO check if image is allowed. Is yes, pull it from repo.
    
    if not docker_client.images.list(name=image_uri):
      logger.debug("Image {} not found on this node, pulling it...".format(image_uri))
      docker_client.images.pull(image_uri, tag="latest")
    
    cont_name = "FVE" + "_" + image_uri.replace("/", "-").replace(":", "-") + "_" + '{0:%Y%m%d-%H%M%S-%f}'.format(datetime.datetime.now())

    logger.debug("Deploying container {} with image {}{}".format(
      cont_name,
      image_uri,
      " and command '{}'".format(command) if command else ""
      )
    )

    try:
      docker_client.containers.run(image_uri, name=cont_name, detach=True, stdin_open=True, tty=True, publish_all_ports=True, restart_policy={"Name": "on-failure", "MaximumRetryCount": 3}, command=command, entrypoint=entrypoint)
    except docker.errors.ImageNotFound as e:
      return {"message": str(e)}, 404

    container = docker_client.containers.get(cont_name)

    cont_ip = container.attrs["NetworkSettings"]["IPAddress"]
    logger.debug(cont_ip)

    port_mappings = []

    ports_dict = container.attrs["NetworkSettings"]["Ports"]
    for cont_port in ports_dict:
      for host_port_dict in ports_dict[cont_port]:
        port_map = "{}:{}->{}".format(host_port_dict["HostIp"], host_port_dict["HostPort"], cont_port)
        port_mappings.append(port_map)
        logger.debug(port_map)

    return {"message": "Deployed image {}".format(image_uri),
        "name": cont_name,
        "cont_ip": cont_ip,
        "port_mappings": port_mappings
        }, 201

  # TODO def delete(self):
     

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

### MAIN

if __name__ == '__main__':

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
  parser.add_argument("--collector-address", help="Collector endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
  parser.add_argument("--collector-port", help="Collector endpoint TCP port, dafault: 5003", nargs="?", default=5003)
  parser.add_argument("--repo-address", help="Image repo endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
  parser.add_argument("--repo-port", help="Image repo endpoint TCP port, default: 5006", nargs="?", default=5006)
  parser.add_argument("-w", "--wait-remote", help="Wait for remote endpoint(s), default: false", action="store_true", default=False)
  parser.add_argument("-d", "--debug", help="Run in debug mode, default: false", action="store_true", default=False)
  
  args = parser.parse_args()
  
  ep_address = args.address
  ep_port = args.port
  collector_address = args.collector_address
  collector_port = args.collector_port
  repo_address = args.repo_address
  repo_port = args.repo_port
  wait_remote = args.wait_remote
  debug = args.debug

  if wait_remote:
    wait_for_remote_endpoint(collector_address, collector_port)
    wait_for_remote_endpoint(repo_address, repo_port)

  ### API definition

  app = Flask(__name__)
  api = Api(app)
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, "/info")
  api.add_resource(FogApplicationList, '/apps')
  api.add_resource(FogApplication, '/app/<app_id>')
  api.add_resource(FogVirtEngineList, '/fves')
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

  app.run(host=ep_address, port=ep_port, debug=debug)
  
