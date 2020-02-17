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

import docker

import fnode_agent as fnagent

### Docker

docker_client = docker.from_env()

### Resource definition

class Test(Resource):
  def get(self):
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class FogApplication(Resource):

  def __init__(self, *args, **kwargs):
    super(FogApplication, self).__init__()
    self.fna = kwargs["fna"]

  def post(self, app_id):
    # retrieve information from POST body
    req_json = request.get_json(force=True)
    image_uri = req_json["image_uri"]
    command = ""
    if "command" in req_json:
      command = req_json["command"]
    entrypoint = ""
    if "entrypoint" in req_json:
      entrypoint = req_json["entrypoint"]

    #logger.debug(f"{image_uri}")
    #resp_json = requests.get("http://{}:{}/image/{}".format(repo_address, repo_port, image_uri)).json()
    #logger.debug("Deploying {}".format(resp_json["name"]))
    #self.fna.set_node_class("S")
    #self.fna.set_node_apps(resp_json["apps"])

    # here try to deploy image image_uri on this node

    # TODO check if image is present on this node. If not, check if image is allowed. Is yes, pull it from repo.
    
    logger.debug("Deploying {}".format(image_uri))

    cont_name = app_id + "-" + image_uri.replace("/", "_") + "-" + '{0:%Y%m%d_%H%M%S_%f}'.format(datetime.datetime.now())

    try:
      docker_client.containers.run(image_uri, name=cont_name, detach=True, stdin_open=True, tty=True, publish_all_ports=True, restart_policy={"Name": "on-failure", "MaximumRetryCount": 3}, command=command, entrypoint=entrypoint)
    except docker.errors.ImageNotFound as e:
      return {"message": str(e)}, 404

    with open("/tmp/{}.json".format(cont_name), "w") as f:
      json.dump({"image": image_uri, "app": app_id}, f)

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
        "Name": cont_name,
        "IPAddress": cont_ip,
        "PortMappings": port_mappings
        }, 201

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

#class FogNodeIaaS(threading.Thread):
#  def __init__(self, ep_address, ep_port, repo_address, repo_port, logger=None):
#    super().__init__()
#    self.ep_address = ep_address
#    self.ep_port = ep_port
#    self.repo_address = repo_address
#    self.repo_port = repo_port
#    self.logger = logger
#
#    ### API definition
#    self.app = Flask(__name__)
#    self.api = Api(self.app)
#    self.api.add_resource(Test, '/test')
#    self.api.add_resource(FogApplication, '/app')
#
#  def run(self):
#    self.app.run(host=ep_address, port=ep_port, debug=True)
    

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
  parser.add_argument("-n", "--num-agents", help="Number of FogNodeAgents to spawn, default: 1", type=int, nargs="?", default=1)
  parser.add_argument("-l", "--limit-updates", help="Number of updates to send before quitting, default: 0 (infinite)", type=int, nargs="?", default=0)
  parser.add_argument("-i", "--update-interval", help="Update interval in seconds, default: 10", type=int, nargs="?", default=10)
  parser.add_argument("-w", "--wait-remote", help="Wait for remote endpoint(s), default: false", action="store_true", default=False)
  
  args = parser.parse_args()
  
  ep_address = args.address
  ep_port = args.port
  collector_address = args.collector_address
  collector_port = args.collector_port
  repo_address = args.repo_address
  repo_port = args.repo_port
  n_agents = args.num_agents
  lim_updates = args.limit_updates
  interval = args.update_interval
  wait_remote = args.wait_remote

  if wait_remote:
    wait_for_remote_endpoint(collector_address, collector_port)
    wait_for_remote_endpoint(repo_address, repo_port)

  fna = fnagent.FogNodeAgent(collector_address, collector_port, node_ipv4=ep_address, name="_FNA{:03d}_".format(0), node_class="I", logger=logger, lim=lim_updates, period=interval)

  ### API definition
  app = Flask(__name__)
  api = Api(app)
  api.add_resource(Test, '/test')
  api.add_resource(FogApplication, '/app/<app_id>', resource_class_kwargs={"fna":fna})

  #fnode_iaas = FogNodeIaaS(ep_address, ep_port, repo_address, repo_port, logger=logger)
  #fnode_iaas.start()

  #fna.start()

  app.run(host=ep_address, port=ep_port, debug=True)
  
  #try:
  #  while True:
  #    sleep(1)
  #except KeyboardInterrupt:
  #  docker_client.containers.get("apache").stop()
  #  docker_client.containers.prune()
    

