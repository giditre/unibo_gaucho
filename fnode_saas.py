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

### Logging setup
  
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
 
### Docker

docker_client = docker.from_env()

###

thread_list = []

###

def shell_command(cmd, track_pid=False, pid_dir="/tmp"):
  logger.debug("Shell cmd: {}".format(cmd))
  os.system(cmd)

###

class StressThread(threading.Thread):
  def __init__(self, *args, **kwargs):
    super().__init__()
    _handled_parameters = [ "timeout", "cpu" ]
    self.parameters_dict = {}
    for p in _handled_parameters:
      if p in kwargs:
        self.parameters_dict[p] = kwargs[p]

  def run(self):
    # Example: stress --cpu 8 --io 4 --vm 2 --vm-bytes 128M --timeout 10s
    cmd = "stress " +  " ".join( [ "--{} {}".format(k, v) for k, v in self.parameters_dict.items() ] )
    shell_command(cmd)

  def stop(self):
    cmd = "killall stress"
    shell_command(cmd)

### Resource definition

class Test(Resource):
  def get(self):
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class FogNodeInfo(Resource):
  def get(self):
    return {"class": "S"}

class FogApplicationList(Resource):
  def get(self):
    # TODO make it not hardcoded but get the identifier somewhere
    # TODO count the instances of each app currently running on this node
    apps = {"FA002": 1}
    return {"apps": apps}
      
  def delete(self):
    # remove instances of running apps if possible
    global thread_list
    for t in thread_list:
      t.stop()
    resp = "Stopped all apps."
    return {"message": resp}, 200

class FogApplication(Resource):

  def post(self, app_id):
    # retrieve information from POST body
    req_json = request.get_json(force=True)
    
    logger.debug("Running app {} with parameters '{}'".format(app_id, req_json))

    if app_id == "FA002":
      t = StressThread(**req_json)
      t.start()
      thread_list.append(t)

    return {
      "message": "Running app {}".format(app_id),
      "hostname": socket.gethostname()
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


### MAIN

if __name__ == '__main__':

 
  ### Command line argument parsing
  
  parser = argparse.ArgumentParser()
  
  parser.add_argument("address", help="Endpoint IP address")
  parser.add_argument("port", help="Endpoint TCP port")
  parser.add_argument("--collector-address", help="Collector endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
  parser.add_argument("--collector-port", help="Collector endpoint TCP port, default: 5003", nargs="?", default=5003)
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

  ### API definition
  app = Flask(__name__)
  api = Api(app)
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(FogApplicationList, '/apps')
  api.add_resource(FogApplication, '/app/<app_id>')

  #fnode_iaas = FogNodeIaaS(ep_address, ep_port, repo_address, repo_port, logger=logger)
  #fnode_iaas.start()

  app.run(host=ep_address, port=ep_port, debug=True)
  
  #try:
  #  while True:
  #    sleep(1)
  #except KeyboardInterrupt:
  #  docker_client.containers.get("apache").stop()
  #  docker_client.containers.prune()
    

