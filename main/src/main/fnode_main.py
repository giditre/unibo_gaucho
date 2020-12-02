import logging
from logging.config import fileConfig
from pathlib import Path
fileConfig(str(Path(__file__).parent.joinpath("logging.ini")))
logger = logging.getLogger(__name__)
logger.info(f"Load {__name__} with {logger}")

from ipaddress import IPv4Address
import time

from flask import Flask, request
from flask_restful import Resource, Api

import forch
logger.debug("IS_ORCHESTRATOR: {}".format(forch.is_orchestrator()))


class FNVI(object):
  __key = object()
  __instance = None

  def __init__(self, *, key=None):
    assert key == self.__class__.__key, "There can only be one {0} object and it can only be accessed with {0}.get_instance()".format(self.__class__.__name__)
    self.__sa = forch.SLPFactory.create_SA()
    # TODO prendere json_file_name in altro modo
    self.__service_list = self.load_service_json(str(Path(__file__).parent.joinpath("service_example.json").absolute()))
    
    self.register_service_list(self.__service_list)

  @classmethod
  def get_instance(cls):
    if cls.__instance is None:
      cls.__instance = cls(key=cls.__key)
    return cls.__instance

  def __get_SA(self):
    return self.__sa

  def get_service_list(self):
    return self.__service_list

  def register_service(self, service):
    logger.info(f"Register service {service}")
    self.__get_SA().register_service(service)

  def register_service_list(self, service_list):
    for service in service_list:
      self.register_service(service)

  def load_service_json(self, json_file_name):
    if forch.is_orchestrator():
      ipv4 = IPv4Address("127.0.0.1")
    else:
      # TODO G: prendere indirizzo IP da interfaccia usata sulla rete fog
      ipv4 = IPv4Address("192.168.64.123")
    
    return forch.Service.create_services_from_json(ipv4, json_file_name)

### instantiate components

FNVI.get_instance()

### API Resources

class Test(Resource):
  def get(self):
    return {
      "message": f"This component ({Path(__file__).name}) is up!",
      "type": "TEST_OK"
    }

if __name__ == '__main__':
  ### Command line argument parser
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("address", help="This component's IP address", nargs="?", default="127.0.0.1")
  parser.add_argument("port", help="This component's TCP port", type=int, nargs="?", default=6001)
  parser.add_argument("-d", "--debug", help="Run in debug mode, default: false", action="store_true", default=False)
  args = parser.parse_args()

  app = Flask(__name__)

  api = Api(app)
  
  api.add_resource(Test, '/test')

  # api.add_resource(FogServices, '/services', '/services/<s_id>')
  
  try:
    app.run(host=args.address, port=args.port, debug=args.debug)
  except KeyboardInterrupt:
    pass
  finally:
    logger.info("Cleanup after interruption") # TODO: questo pare non venga mai eseguito
