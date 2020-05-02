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
import socket

### Docker

docker_client = docker.from_env()

###

cont_name = ''

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
      "type": "FVE_DOCK_IMG_NF",
      "message": str(e)
    }, 404

  container = docker_client.containers.get(cont_name)

  return container

### Resource definition

class Test(Resource):
  def get(self):
    return {
      "message": "This endpoint ({} at {}) is up!".format(os.path.basename(__file__), socket.gethostname()),
      "type": "FVE_DOCK_TEST_OK"
    }

class FogNodeInfo(Resource):
  def get(self):
    return {
      "type": "FVE_DOCK_INFO",
      "class": "I"
    }


class FogVirtEngine(Resource):

  def post(self, fve_id):
    global cont_name
    if cont_name:
      return {
        "type": "FVE_DOCK_BUSY",
        "message": "Busy"
      }, 400

    # retrieve information from POST body
    req_json = request.get_json(force=True)
    
    image_uri = ""
    if "image_uri" in req_json:
      image_uri = req_json["image_uri"]
    else:
      return {
        "message": "Image URI not specified",
        "type": "FVE_DOCK_IMG_NSPC"
      }, 400

    command = ""
    if "command" in req_json:
      command = req_json["command"]

    entrypoint = ""
    if "entrypoint" in req_json:
      entrypoint = req_json["entrypoint"]

    # here try to deploy image image_uri on this node
    container = run_container(fve_id, image_uri, command, entrypoint)

    cont_name = container.name
    cont_ip = container.attrs["NetworkSettings"]["IPAddress"]
    #logger.debug(cont_ip)

    port_mappings = []

    ports_dict = container.attrs["NetworkSettings"]["Ports"]
    for cont_port in ports_dict:
      for host_port_dict in ports_dict[cont_port]:
        port_map = "{}:{}->{}".format(host_port_dict["HostIp"], host_port_dict["HostPort"], cont_port)
        port_mappings.append(port_map)
        logger.debug(port_map)

    return {
        "message": "Deployed image {}".format(image_uri),
        "type": "FVE_DOCK_CONT_DEPL",
        "name": cont_name,
        #"cont_ip": cont_ip,
        "port_mappings": port_mappings
        }, 201

  def delete(self, fve_id):
    global cont_name
    for cont in docker_client.containers.list():
      if cont.name == cont_name:
        cont.stop()
    cont_name = ''
    resp = docker_client.containers.prune()
    return {
      "message": resp,
      "type": "FVE_DOCK_DEL"
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
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

  app.run(host=ep_address, port=ep_port, debug=debug)
  
