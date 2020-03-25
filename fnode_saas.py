from flask import Flask, request
from flask_restful import Resource, Api, reqparse, abort
import argparse
import requests
import logging
import random
from time import sleep
import os
import threading
import socket

### Logging setup
  
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
 
###

thread_list = []

###

def shell_command(cmd, track_pid=False, pid_dir="/tmp"):
  logger.debug("Shell cmd: {}".format(cmd))
  os.system(cmd)

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
      resp = requests.delete("http://127.0.0.1:{}/app/{}".format(t.get_port(), t.get_app_id())
    resp = "Stopped all apps."
    return {"message": resp}, 200

class FogApplication(Resource):

  def post(self, app_id):
    # retrieve information from POST body
    req_json = request.get_json(force=True)
    
    if app_id == "FA002":
      
      msg = "Deployed app {}".format(app_id, req_json)
      logger.debug(msg)
      
      t = StressThread(app_id, **req_json)
      t.start()
      thread_list.append(t)

      return {
        "message": msg,
        "hostname": socket.gethostname(),
        "port": t.get_port()
      }, 201

    else:
      msg = "Unrecognized app {}".format(app_id)
      return {"message": msg}, 404

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

###

class StressThread(threading.Thread):
  def __init__(self, app_id, *args, **kwargs):
    super().__init__()

    # parse handled parameters (application specific)
    _handled_parameters = [ "timeout", "cpu" ]
    self.parameters_dict = {}
    for p in _handled_parameters:
      if p in kwargs:
        self.parameters_dict[p] = kwargs[p]

    self.app_id = app_id

    # select random port
    self.port = random.randint(30000, 40000)
    # check if port is in use and keep selecting new port until free port found
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
      while s.connect_ex(('localhost', self.port)) == 0:
        self.port = random.randint(30000, 40000)
          
    # TODO find better way of running a separate thread offering its own API
    self.cmd = "python3 fnode_stress.py 0.0.0.0 {}".format(self.port) 

  def run(self):
    shell_command(self.cmd)

  def get_app_id(self):
    return self.app_id

  def get_port(self):
    return self.port

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
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(FogApplicationList, '/apps')
  api.add_resource(FogApplication, '/app/<app_id>')

  app.run(host=ep_address, port=ep_port, debug=debug)
  
