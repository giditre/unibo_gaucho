from flask import Flask, request
from flask_restful import Resource, Api
import argparse
import logging
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
    return {"message": "This endpoint ({} at {}) is up!".format(os.path.basename(__file__), socket.gethostname())}

class FogNodeInfo(Resource):
  def get(self):
    return {"app": "FA002"}

class FogApplication(Resource):

  def post(self, app_id):
    # retrieve information from POST body
    req_json = request.get_json(force=True)
    
    msg = "Running app {} with parameters '{}'".format(app_id, req_json)

    logger.debug(msg)

    t = StressThread(**req_json)
    t.start()
    thread_list.append(t)

    return {
      "message": msg,
      "hostname": socket.gethostname()
    }, 201

  def delete(self, app_id):
    for t in thread_list:
      t.stop()
    return {
      "message": "Stopped app {}".format(app_id),
      "hostname": socket.gethostname()
    }, 200

### MAIN

if __name__ == '__main__':

 
  ### Command line argument parsing
  
  parser = argparse.ArgumentParser()
  
  parser.add_argument("address", help="Endpoint IP address")
  parser.add_argument("port", help="Endpoint TCP port")
  parser.add_argument("-d", "--debug", help="Run in debug mode, default: false", action="store_true", default=False)
  
  args = parser.parse_args()
  
  ep_address = args.address
  ep_port = args.port
  debug = args.debug

  ### API definition
  app = Flask(__name__)
  api = Api(app)
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(FogApplication, '/app/<app_id>')

  app.run(host=ep_address, port=ep_port, debug=debug)
  
