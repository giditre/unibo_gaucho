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
import socket
import docker

### Docker

docker_client = docker.from_env()

###

thread_list = []

###

def shell_command(cmd, track_pid=False, pid_dir="/tmp"):
  logger.debug("Shell cmd: {}".format(cmd))
  os.system(cmd)

def run_container(service_id, image_uri, command="", entrypoint=""):
  # check if image is present on this node. If not, TODO check if image is allowed. Is yes, pull it from repo.

  if not docker_client.images.list(name=image_uri):
    logger.debug("Image {} not found on this node, pulling it...".format(image_uri))
    docker_client.images.pull(image_uri, tag="latest")

  cont_name = service_id + "_" + image_uri.replace("/", "-").replace(":", "-") + "_" + '{0:%Y%m%d-%H%M%S-%f}'.format(datetime.datetime.now())
  cont_hostname = cont_name if len(cont_name) <= 63 else cont_name[:63]

  logger.debug("Deploying service {} in container {} with image {}{}".format(service_id, cont_name, image_uri,
    " and command '{}'".format(command) if command else ""))

  try:
    docker_client.containers.run(image_uri, name=cont_name, hostname=cont_hostname, detach=True, stdin_open=True, tty=True, publish_all_ports=True, restart_policy={"Name": "on-failure", "MaximumRetryCount": 3}, command=command, entrypoint=entrypoint)
  except docker.errors.ImageNotFound as e:
    return {
      "message": str(e),
      "type": "NIM_IMG_NF"
    }, 404

  container = docker_client.containers.get(cont_name)

  return container

### Resource definition

class Test(Resource):
  def get(self):
    return {
      "message": "This endpoint ({}) is up!".format(os.path.basename(__file__)),
      "type": "NIM_TEST_OK"
    }

class FogNodeInfo(Resource):
  def get(self):
    return {
      "type": "NIM_INFO",
      "class": "I"
    }

class FogApplicationList(Resource):
  def get(self):
    app_counter = Counter([ cont.name.split("_")[0] for cont in docker_client.containers.list() if cont.name.startswith("APP")])
    return {
      "type": "NIM_APP_LIST",
      "apps": dict(app_counter)
    }
      
  def delete(self):
    for cont in docker_client.containers.list():
      if cont.name.startswith("APP"):
        cont.stop()
    resp = docker_client.containers.prune()
    return {
      "message": resp,
      "type": "NIM_APP_DEL"
    }, 200

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

    container = run_container(app_id, image_uri, command, entrypoint)

    cont_name = container.name
    cont_ip = container.attrs["NetworkSettings"]["IPAddress"]
    #logger.debug(cont_name, cont_ip)

    port_mappings = []

    ports_dict = container.attrs["NetworkSettings"]["Ports"]
    for cont_port in ports_dict:
      for host_port_dict in ports_dict[cont_port]:
        port_map = "{}:{}->{}".format(host_port_dict["HostIp"], host_port_dict["HostPort"], cont_port)
        port_mappings.append(port_map)
        logger.debug(port_map)

    return {
      "message": "Deployed APP {} with image {}".format(app_id, image_uri),
      "type": "NIM_APP_DEPL",
      "name": cont_name,
      "cont_ip": cont_ip,
      "port_mappings": port_mappings
      }, 201

class SoftDevPlatformList(Resource):
  def get(self):
    sdp_counter = Counter([ cont.name.split("_")[0] for cont in docker_client.containers.list() if cont.name.startswith("SDP")])
    return {"sdps": dict(sdp_counter)}, 200
      
  def delete(self):
    for cont in docker_client.containers.list():
      if cont.name.startswith("SDP"):
        cont.stop()
    resp = docker_client.containers.prune()
    return {
      "message": resp,
      "type": "NIM_SDP_DEL"
    }, 200

class SoftDevPlatform(Resource):

  def post(self, sdp_id):
    # retrieve information from POST body
    req_json = request.get_json(force=True)
    
    image_uri = ""
    if "image_uri" in req_json:
      image_uri = req_json["image_uri"]
    else:
      # TODO: GET the image by sdp_id from forch_iaas_mgmt
      pass

    command = ""
    if "command" in req_json:
      command = req_json["command"]

    entrypoint = ""
    if "entrypoint" in req_json:
      entrypoint = req_json["entrypoint"]

    # here try to deploy image image_uri on this node
    container = run_container(sdp_id, image_uri, command, entrypoint)

    cont_name = container.name
    cont_ip = container.attrs["NetworkSettings"]["IPAddress"]
    logger.debug(cont_ip)

    port_mappings = []

    ports_dict = container.attrs["NetworkSettings"]["Ports"]
    for cont_port in ports_dict:
      for host_port_dict in ports_dict[cont_port]:
        port_map = "{}:{}->{}".format(host_port_dict["HostIp"], host_port_dict["HostPort"], cont_port)
        port_mappings.append(port_map)
        logger.debug(port_map)

    return {
      "message": "Deployed SDP {} with image {}".format(sdp_id, image_uri),
      "type": "NIM_SDP_DEPL",
      "name": cont_name,
      "cont_ip": cont_ip,
      "port_mappings": port_mappings
      }, 201

class FogVirtEngineList(Resource):

  def get(self):
    fve_counter = Counter([ cont.name.split("_")[0] for cont in docker_client.containers.list() if cont.name.startswith("FVE")])
    fve_counter.update({"FVE001": 1})
    return {
      "type": "NIM_FVE_LIST",
      "fves": dict(fve_counter)
    }, 200

  def delete(self):
    for cont in docker_client.containers.list():
      if cont.name.startswith("FVE"):
        cont.stop()
    resp = docker_client.containers.prune()
    return {
      "message": resp,
      "type": "NIM_FVE_DEL"
    }, 200

class DockerFVEThread(threading.Thread):
  def __init__(self, fve_id, *args, **kwargs):
    super().__init__()

    ## parse handled parameters (application specific)
    #_handled_parameters = [ "timeout", "cpu" ]
    #self.parameters_dict = {}
    #for p in _handled_parameters:
    #  if p in kwargs:
    #    self.parameters_dict[p] = kwargs[p]

    self.fve_id = fve_id

    # select random port
    self.port = random.randint(30000, 40000)
    # check if port is in use and keep selecting new port until free port found
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
      while s.connect_ex(('localhost', self.port)) == 0:
        self.port = random.randint(30000, 40000)

    # TODO find better way of running a separate thread offering its own API
    self.cmd = "python3 fnode_fve_docker.py 0.0.0.0 {}".format(self.port)

  def run(self):
    shell_command(self.cmd)

  def get_fve_id(self):
    return self.fve_id

  def get_port(self):
    return self.port

class FogVirtEngine(Resource):

  def post(self, fve_id):
    # retrieve information from POST body
    req_json = request.get_json(force=True)

    if fve_id == "FVE001":
      msg = "Deployed FVE {}".format(fve_id, req_json)
      logger.debug(msg)

      t = DockerFVEThread(fve_id, **req_json)
      t.start()
      thread_list.append(t)

      return {
        "message": msg,
        "type": "NIM_FVE_DEPL",
        "hostname": socket.gethostname(),
        "port": t.get_port()
      }, 201

    else:
      msg = "Unrecognized FVE {}".format(fve_id)
      return {
        "message": msg,
        "type": "NIM_FVE_NDEF"
      }, 400
      

  # TODO def delete(self):     

class DockerImageList(Resource):

  def get(self):
    img_counter = Counter([ img.tags[0] for img in docker_client.images.list() ])
    return {
      "type": "NIM_IMG_LIST",
      "imgs": dict(img_counter)
    }, 200

  def delete(self):
    resp = docker_client.images.prune(prune(filters={"dangling":False}))
    return {
      "message": resp,
      "type": "NIM_IMG_DEL"
    }, 200

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

  api.add_resource(SoftDevPlatformList, '/sdps')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')

  api.add_resource(FogVirtEngineList, '/fves')
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

  api.add_resource(DockerImageList, '/imgs')

  app.run(host=ep_address, port=ep_port, debug=debug)
  
