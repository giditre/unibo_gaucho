import logging
from logging.config import fileConfig
from pathlib import Path
fileConfig(str(Path(__file__).parent.joinpath("logging.ini")))
logger = logging.getLogger(__name__)
logger.info(f"Load {__name__} with {logger}")

from time import sleep

from flask import Flask, request, jsonify
from flask_restful import Resource, Api, reqparse, abort

import forch
forch.set_orchestrator()

logger.debug("IS_ORCHESTRATOR: {}".format(forch.is_orchestrator()))


class FOB(object):
  __key = object()
  __instance = None

  def __init__(self, *, key=None):
    assert key == self.__class__.__key, "There can only be one {0} object and it can only be accessed with {0}.get_instance()".format(self.__class__.__name__)

  @classmethod
  def get_instance(cls):
    if cls.__instance is None:
      cls.__instance = cls(key=cls.__key)
    return cls.__instance

  @staticmethod
  def get_service_list():
    return FORS.get_instance().get_service_list()

  @staticmethod
  def allocate(s_id):
    """Takes service ID and returns a Service object or None."""
    s_list = FORS.get_instance().get_service_list()
    s_id_list = [ s.get_id() for s in s_list ]
    if s_id in s_id_list:
      # need to check which node is best suited to host the service
      # first get instance of requested service
      s = next(s for s in s_list if s.get_id() == s_id)
      # then use retrieve_measurement to populate metrics with measurements
      # TODO this is a responsibility of FOVIM
      s.retrieve_measurements()
      # then pick most suitable node
      sn = s.get_node_by_metric() # by default returns node with minimum CPU utilization
      # TODO check if best node is compliant with constraints (e.g.: if min CPU is lower than threshold for allocation)
      if True:
        # if yes, trigger the requested allocation through FOVIM
        FOVIM.get_instance().process_allocation(service_id=s_id, node_id=sn.get_id())
        # TODO: get response and return it to user --> 200 OK
      else:
        # if no, service might be deployed on a new node, so continue
        pass
    
    # we get here if service is not deployed (or unknown), or deployed but on nodes that are too busy
    # check if service is deployable (e.g.: "by deploying an APP on a IaaS node")
    # TODO gather list of available sources (SDP codeblocks and FVE images) from FOVIM (reword explanation)

    # TODO check if there is a source that offers the requested service

      # TODO if yes, check if there is a node that offers the required SDP/FVE for the source, and is free enough to host it ( get_node_by_metric() )
      
        # TODO if yes deploy the source and allocate service on it --> 201 Created

        # TODO if no, there are no more resources for new deployments --> 503 Service Unavailable

      # TODO if no, impossible to deploy service in virtualized way (or unknown service) --> 501 Not Implemented

    


class FORS(object):
  __key = object()
  __instance = None

  @classmethod
  def get_instance(cls):
    if cls.__instance is None:
      cls.__instance = cls(key=cls.__key)
    return cls.__instance

  def __init__(self, *, key=None):
    assert key == self.__class__.__key, "There can only be one {0} object and it can only be accessed with {0}.get_instance()".format(self.__class__.__name__)
    self.__sc = forch.ServiceCache()

  def __get_service_cache(self):
    return self.__sc

  def get_service_list(self):
    self.__get_service_cache().refresh()
    return self.__sc.get_list()


class FOVIM(object):
  __key = object()
  __instance = None

  def __init__(self, *, key=None):
    assert key == self.__class__.__key, "There can only be one {0} object and it can only be accessed with {0}.get_instance()".format(self.__class__.__name__)
    self.__da = forch.SLPFactory.create_DA()

  @classmethod
  def get_instance(cls):
    if cls.__instance is None:
      cls.__instance = cls(key=cls.__key)
    return cls.__instance

  @staticmethod
  def process_allocation(*, service_id, node_id):
    # check if service is already deployed (e.g.: an APP offered by a SaaS node)
    # 
    pass

### start components

FORS.get_instance()
FOVIM.get_instance()

### API Resources

class Test(Resource):
  def get(self):
    return {
      "message": f"This component ({Path(__file__).name}) is up!",
      "type": "FOCO_TEST_OK"
    }

class FogServices(Resource):
  def get(self, s_id=""):
    """Gather list of services and format it in a response."""
    # get list of services
    s_list = FOB.get_instance().get_service_list()
    # format response based on request
    s_id_list = [ s.get_id() for s in s_list ]
    # check if a service was specified
    if s_id:
      if s_id in s_id_list:
        return {
          "message": f"Requested service {s_id} found.",
          # "type": "FOCO_SERV_OK",
          "services": [ s_id ]
        }
      else:
        return {
          "message": f"Requested service {s_id} not found.",
          # "type": "FOCO_SERV_LIST",
          "services": []
        }, 404
    else:
      return {
        "message": f"Found {len(s_list)} service(s).",
        # "type": "FOCO_SERV_LIST",
        "services": [ s.get_id() for s in s_list ]
      }

  def post(self, s_id):
    """Submit request for allocation of a service."""
    s = FOB.get_instance().allocate(s_id)
    if s is None:
      # service not found
      return {
          "message": f"Requested service {s_id} not found."
          # "type": "FOCO_SERV_POST",
          # "services": []
        }, 404
    elif isinstance(s, forch.Service):
      assert len(s.get_node_list()) in [0,1], "Too many ServiceNodes!"
      if len(s.get_node_list()) == 0:
        return {
        "message": f"Service {s.get_id()} unavailable."
        # "type": "FOCO_SERV_POST"
        }, 503
      elif len(s.get_node_list()) == 1:
        return {
          "message": f"Service {s.get_id()} allocated on node {s.get_node_list()[0]}."
          # "type": "FOCO_SERV_POST"
        }, 201

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
    # del fovim
    # del fors