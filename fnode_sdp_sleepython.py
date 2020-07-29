from flask import Flask, request
from flask_restful import Resource, Api
import argparse
import logging
import os
import threading
import multiprocessing
import socket
import time

### Logging setup
  
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(filename)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
 
###

sdp_process = None

###

class PythonSDP():
  def __init__(self, *args, **kwargs):
    self.output = []
    self.done = False

  def exec_code(self, code):
    exec(code, {'__builtins__': __builtins__}, {"print": self.store_output, "time": time.time, "sleep": time.sleep})
    self.done = True
    #print("sdp done", self.is_done())

  def store_output(self, text):
    self.output.append(text)
    #print("func", self.output)

  def get_output_str(self):
    return "\n".join(self.output)

  def is_done(self):
    return self.done

def python_sdp_target(sdp, out_q, *args, **kwargs):
  handled_parameters = [ "code", "requirements" ]
  parameters_dict = {}
  for p in handled_parameters:
    if p in kwargs:
      parameters_dict[p] = kwargs[p]

  #exec(parameters_dict["code"], {"print": store_output})
  sdp.exec_code(parameters_dict["code"])
  out_q.put(sdp)

### Resource definition

class Test(Resource):
  def get(self):
    return {
      "message": "This endpoint ({} at {}) is up!".format(os.path.basename(__file__), socket.gethostname()),
      "type": "SDP_SLPY_TEST_OK"
    }

class FogNodeInfo(Resource):
  def get(self):
    return {
      "sdp": "SDP003",
      "type": "SDP_SLPY_INFO"
    }

class SoftDevPlatform(Resource):

  def post(self, sdp_id):

    global sdp_process

    if sdp_process and sdp_process.is_alive():
      return {
        "message": "Busy",
        "type": "SDP_SLPY_BUSY",
        "hostname": socket.gethostname()
      }, 503

    # retrieve information from POST body
    req_json = request.get_json(force=True)
    
    msg = "Running SDP {}".format(sdp_id)

    logger.debug(msg)

    sdp = PythonSDP()

    q = multiprocessing.Queue()

    sdp_process = multiprocessing.Process(target=python_sdp_target, args=(sdp, q), kwargs=req_json)
    sdp_process.start()

    output = ""
    if "return_output" in req_json and req_json["return_output"] == True:
      #print("post", sdp.get_output_str(), "done", sdp.is_done())
      sdp_process.join()
      sdp = q.get()
      #print("post", sdp.get_output_str())
      msg = "Finished running SDP {}".format(sdp_id)
      output = sdp.get_output_str()

    return {
      "message": msg,
      "type": "SDP_SLPY_EXEC",
      "params": req_json,
      "hostname": socket.gethostname(),
      "output": output
    }, 201  

  def delete(self, sdp_id):
    if sdp_process:
      sdp_process.terminate()
      msg = "SDP {} terminated".format(sdp_id)
    else:
      msg = "No running SDP to terminate"
    return {
      "message": msg,
      "type": "SDP_SLPY_DEL",
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
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')

  app.run(host=ep_address, port=ep_port, debug=debug)
  
