from flask import Flask, request
from flask_restful import Resource, Api, reqparse, abort
import json
import argparse
import requests
import logging
import random
from time import sleep
import os
import threading
import fnode_agent as fnagent

### Resource definition

class Test(Resource):
  def get(self):
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class FogApplication(Resource):

  def __init__(self, *args, **kwargs):
    super(FogApplication, self).__init__()
    self.fna = kwargs["fna"]

  def post(self):
    # retrieve information from POST body
    image_uri = request.get_json(force=True)["image_uri"]
    #logger.debug(f"{image_uri}")
    r = requests.get("http://{}:{}/image/{}".format(repo_address, repo_port, image_uri)).json()
    logger.debug("Deploying {}".format(r["name"]))
    self.fna.set_node_class("S")
    return {"message": "Deploying {}".format(r["name"])}, 201

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
  parser.add_argument("--collector-address", help="Collector endpoint IP address", nargs="?", default="127.0.0.1")
  parser.add_argument("--collector-port", help="Collector endpoint TCP port", nargs="?", default=5003)
  parser.add_argument("--repo-address", help="Image repo endpoint IP address", nargs="?", default="127.0.0.1")
  parser.add_argument("--repo-port", help="Image repo endpoint TCP port", nargs="?", default=5006)
  parser.add_argument("-n", "--num-agents", help="Number of FogNodeAgents to spawn", type=int, nargs="?", default=1)
  parser.add_argument("-l", "--limit-updates", help="Number of updates to send before quitting", type=int, nargs="?", default=0)
  parser.add_argument("-i", "--update-interval", help="Update interval in seconds", type=int, nargs="?", default=10)
  
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

  wait_for_remote_endpoint(collector_address, collector_port)
  wait_for_remote_endpoint(repo_address, repo_port)

  fna = fnagent.FogNodeAgent(collector_address, collector_port, name="_FNA{:03d}_".format(0), node_class="I", logger=logger, lim=lim_updates, period=interval)

  ### API definition
  app = Flask(__name__)
  api = Api(app)
  api.add_resource(Test, '/test')
  api.add_resource(FogApplication, '/app', resource_class_kwargs={"fna":fna})

  #fnode_iaas = FogNodeIaaS(ep_address, ep_port, repo_address, repo_port, logger=logger)
  #fnode_iaas.start()

  fna.start()

  app.run(host=ep_address, port=ep_port, debug=False)

