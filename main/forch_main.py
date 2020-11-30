import logging
from logging.config import fileConfig
from pathlib import Path
fileConfig(str(Path(__file__).parent.joinpath("logging.ini")))
logger = logging.getLogger(__name__)
logger.info(f"Load {__name__} with {logger}")

from time import sleep
import json

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
    # gather list of available sources (SDP codeblocks and FVE images)
    # TODO improve loading sources
    with open(str(Path(__file__).parent.joinpath("service_example.json").absolute())) as f:
      sources_dict = json.load(f)
    self.__sources_list = sources_dict["sources"]

  @classmethod
  def get_instance(cls):
    if cls.__instance is None:
      cls.__instance = cls(key=cls.__key)
    return cls.__instance

  def __get_sources_list(self):
    return self.__sources_list

  def __get_source_for_service(self, service_id, *, priority_list=["FVE", "SDP"]):
    """Finds source that implements requested service, prioritizing the base for the service"""
    for p in priority_list:
      try:
        return next(src for src in self.__get_sources_list() if src["service"] == service_id and p in src["base"])
      except StopIteration:
        continue
    return None

  @staticmethod
  def get_service_list():
    return FORS.get_instance().get_service_list()

  def allocate(self, s_id):
    """Takes service ID and returns a Service object or None."""
    s = FORS.get_instance().get_service(s_id, refresh_sc=True, refresh_meas=True)
    if s is not None:
      # it means that the service is defined in the service cache
      # need to check which node is best suited to host the service
      sn = s.get_node_by_metric() # by default returns node with minimum CPU utilization
      if sn is not None:
        # TODO check if best node is compliant with constraints (e.g.: if min CPU is lower than threshold for allocation)
        if True: # TODO set meaningful condition
          # if yes, trigger the requested allocation through FOVIM
          FOVIM.get_instance().process_allocation(service_id=s_id, node_id=sn.get_id())
          # TODO get response and return it to user --> 200 OK
        else:
          # if no, it means that there are no nodes that are free enough to host this service - it might still be deployable
          # TODO handle this case
          pass
      else:
        # it means that there are no service nodes registered to this service - it might still be deployable
        # TODO handle this case
        pass
    
    # we get here if the service is not in the service cache or it is but is offered only by busy nodes
    # check if service is deployable (e.g.: "by deploying an APP on a IaaS node"), starting by looking for a source that offers the requested service
    src = self.__get_source_for_service(s_id)
    # check if there is a source that offers the requested service
    if src is not None:
      # TODO if yes, check if there is a node that offers the required SDP/FVE for the source, and is free enough to host it ( get_node_by_metric() )
      if True: # TODO set meaningful condition
        # TODO if yes, deploy the source and allocate service on it --> 201 Created
        pass
      else:
        # TODO if no, there are no more resources for new deployments --> 503 Service Unavailable
        pass
    else:
      # TODO if no, unknown service --> 404 Not Found
      pass


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

  def __refresh_service_cache(self):
    self.__get_service_cache().refresh()

  def get_service_list(self, *, refresh_sc=False, refresh_meas=False):
    if refresh_sc:
      self.__refresh_service_cache()
    if refresh_meas:
      return [ s.refresh_measurements() for s in self.__sc.get_list() ]
    return self.__sc.get_list()

  def get_service(self, service_id, *, refresh_sc=False, refresh_meas=False):
    try:
      return next(s for s in self.get_service_list(refresh_sc=refresh_sc, refresh_meas=refresh_meas) if s.get_id() == service_id)
    except StopIteration:
      return None


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