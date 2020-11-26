import logging
from logging.config import fileConfig
from pathlib import Path
# TODO G: prendere configurazione log da file locale (non dentro a src)
fileConfig(str(Path(__file__).parent.joinpath("src").joinpath("forch").joinpath("logging.conf")))
logger = logging.getLogger("fcore")
logger.info(f"Load {__name__} with {logger}")

from time import sleep

from flask import Flask, request, jsonify
from flask_restful import Resource, Api, reqparse, abort

from src.forch.forch_utils_slp import SLPFactory
from src.forch.forch_utils_service import Service
from src.forch.forch_utils_service_cache import ServiceCache

# class FOB():
#   def __init__(self):
#     pass

class FORS():
  def __init__(self):
    self.__sc = ServiceCache()

  def get_service_cache(self):
    return self.__sc

  # TODO: set_service_cache ?

  def get_service_list(self):
    self.get_service_cache().refresh()
    return self.__sc.get_list()

class FOVIM():
  def __init__(self):
    self.__da = SLPFactory.create_DA()

### globals

fovim = FOVIM()
fors = FORS()

### API Resources

class Test(Resource):
  def get(self):
    return {
      "message": f"This component ({Path(__file__).name}) is up!",
      "type": "FOCO_TEST_OK"
    }

class FogServices(Resource):
  def get(self, s_id=""):
    s_list = fors.get_service_list()
    s_id_list = [ s.get_id() for s in s_list ]
    if s_id:
      if s_id in s_id_list:
        return {
          "message": f"Requested service {s_id} found.",
          "type": "FOCO_SERV_OK",
          "services": [ s_id ]
        }
      else:
        return {
          "message": f"Requested service {s_id} not found.",
          "type": "FOCO_SERV_LIST",
          "services": []
        }, 404
    else:
      return {
        "message": f"Found {len(s_list)} service(s).",
        "type": "FOCO_SERV_LIST",
        "services": [ s.get_id() for s in s_list ]
      }

  def post(self, s_id):
    s_list = fors.get_service_list()
    s_id_list = [ s.get_id() for s in s_list ]
    if s_id in s_id_list:
      # need to check which node is best suited to host the service
      # first get instance of requested service
      s = next(s for s in s_list if s.get_id() == s_id)
      # then use retrieve_measurement to populate metrics with measurements
      s.retrieve_measurements()
      # then pick most suitable node
      sn = s.get_node_by_metric() # by default returns node with minimum CPU utilization
      # TODO: instead of returning, trigger the requested allocation
      return {
        "message": f"Service {s} allocated on node {sn}.",
        "type": "FOCO_SERV_POST"
      }
    else:
      # service not available
      return {
          "message": f"Requested service {s_id} not found.",
          "type": "FOCO_SERV_POST",
          "services": []
        }, 404

if __name__ == '__main__':
  ### Command line argument parser
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("address", help="This component's IP address", nargs="?", default="127.0.0.1")
  parser.add_argument("port", help="This component's TCP port", type=int, nargs="?", default=6001)
  # parser.add_argument("--db-json", help="Database JSON file, default: rsdb.json", nargs="?", default="rsdb.json")
  # parser.add_argument("--imgmt-address", help="IaaS management endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
  # parser.add_argument("--imgmt-port", help="IaaS management endpoint TCP port, default: 5004", type=int, nargs="?", default=5004)
  # parser.add_argument("-w", "--wait-remote", help="Wait for remote endpoint(s), default: false", action="store_true", default=False)
  # parser.add_argument("--mon-history", help="Number of monitoring elements to keep in memory, default: 300", type=int, nargs="?", default=300)
  # parser.add_argument("--mon-period", help="Monitoring period in seconds, default: 10", type=int, nargs="?", default=10)
  parser.add_argument("-d", "--debug", help="Run in debug mode, default: false", action="store_true", default=False)
  args = parser.parse_args()

  app = Flask(__name__)

  # @app.before_request
  # def before():
  #   logger.debug("marker start {} {}".format(request.method, request.path))
  
  # @app.after_request
  # def after(response):
  #   logger.debug("marker end {} {}".format(request.method, request.path))
  #   return response

  api = Api(app)
  
  api.add_resource(Test, '/test')

  api.add_resource(FogServices, '/services', '/services/<s_id>')
  
  try:
    app.run(host=args.address, port=args.port, debug=args.debug)
  except KeyboardInterrupt:
    pass
  finally:
    logger.info("Cleanup after interruption") # TODO: questo pare non venga mai eseguito
    del fovim
    del fors