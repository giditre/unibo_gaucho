import logging
from logging.config import fileConfig
from pathlib import Path
fileConfig(str(Path(__file__).parent.joinpath("logging_config.ini")))
logger = logging.getLogger("fcore")
logger.info(f"Load {__name__} with {logger}")

from flask import Flask, request, jsonify
from flask_restful import Resource, Api, reqparse, abort

from src.forch_utils_service import Service
from src.forch_utils_service_cache import ServiceCache

class FORS():
  def __init__(self):
    self.__sc = ServiceCache()

  def get_service_cache(self):
    return self.__sc

  def get_service_list(self):
    self.__sc.refresh()
    return self.__sc.get_list()

class Test(Resource):
  def get(self):
    return {
      "message": f"This component ({Path(__file__).name}) is up!",
      "type": "FOCO_TEST_OK"
    }

fors = FORS()
print(fors.get_service_list())

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
  
  app.run(host=args.address, port=args.port, debug=args.debug)