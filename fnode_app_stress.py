from flask import Flask, request
from flask_restful import Resource, Api
import argparse
import logging
import os
import threading
import socket
import multiprocessing

### Logging setup
  
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(filename)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
 
###

app_process = None

###

def shell_command(cmd, track_pid=False, pid_dir="/tmp"):
  logger.debug("Shell cmd: {}".format(cmd))
  os.system(cmd)

###

#class StressThread(threading.Thread):
#  def __init__(self, *args, **kwargs):
#    super().__init__()
#    _handled_parameters = [ "timeout", "cpu" ]
#    self.parameters_dict = {}
#    for p in _handled_parameters:
#      if p in kwargs:
#        self.parameters_dict[p] = kwargs[p]
#
#  def run(self):
#    # Example: stress --cpu 8 --io 4 --vm 2 --vm-bytes 128M --timeout 10s
#    cmd = "stress " +  " ".join( [ "--{} {}".format(k, v) for k, v in self.parameters_dict.items() ] )
#    shell_command(cmd)
#
#  def stop(self):
#    cmd = "killall stress"
#    shell_command(cmd)

class StressApp():
  def __init__(self, *args, **kwargs):
    self.output = []
    self.done = False

  def run_stress(self, params_dict):
    cmd = "stress " +  " ".join( [ "--{} {}".format(k, v) for k, v in params_dict.items() ] )
    #print(run_stress, cmd)
    shell_command(cmd)

def stress_app_target(app, out_q, *args, **kwargs):
  handled_parameters = [ "timeout", "cpu" ]
  parameters_dict = {}
  for p in handled_parameters:
    if p in kwargs:
      parameters_dict[p] = kwargs[p]

  #print(parameters_dict)

  #parameters_str = " ".join( [ "--{} {}".format(k, v) for k, v in params_dict.items() ]

  app.run_stress(parameters_dict)
  out_q.put(app)

### Resource definition

class Test(Resource):
  def get(self):
    return {
      "message": "This endpoint ({} at {}) is up!".format(os.path.basename(__file__), socket.gethostname()),
      "type": "APP_STRS_TEST_OK"
    }

class FogNodeInfo(Resource):
  def get(self):
    return {
      "type": "APP_STRS_INFO",
      "app": "APP002"
    }

class FogApplication(Resource):

  def post(self, app_id):

    global app_process

    if app_process and app_process.is_alive():
      return {
        "message": "Busy",
        "type": "APP_STRS_BUSY",
        "hostname": socket.gethostname()
      }, 503

    # retrieve information from POST body
    req_json = request.get_json(force=True)
    
    msg = "Running app {} with parameters '{}'".format(app_id, req_json)

    logger.debug(msg)

    app = StressApp()

    q = multiprocessing.Queue()

    #print(app, q)

    app_process = multiprocessing.Process(target=stress_app_target, args=(app, q), kwargs=req_json)
    app_process.start()

    #t = StressThread(**req_json)
    #t.start()
    #thread_list.append(t)

    return {
      "message": msg,
      "type": "APP_STRS_EXEC",
      "params": req_json,
      "hostname": socket.gethostname()
    }, 201

  def delete(self, app_id):
    if app_process:
      app_process.terminate()
      # TODO find a way to avoid using this
      shell_command("killall stress")
      msg = "App {} terminated".format(app_id)
    else:
      msg = "No app process to terminate"
    return {
      "message": msg,
      "type": "APP_STRS_DEL",
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
  api.add_resource(Test, ['/', '/test'])
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(FogApplication, '/app/<app_id>')

  app.run(host=ep_address, port=ep_port, debug=debug)
  
