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
    # gather list of available sources (SDP codelets and FVE images)
    # TODO improve loading sources
    with open(str(Path(__file__).parent.joinpath("service_catalog.json").absolute())) as f:
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
    logger.debug(f"No source found for service {service_id}")
    return None

  @staticmethod
  def get_service_list(*args, **kwargs):
    return FORS.get_instance().get_service_list(*args, **kwargs)

  @staticmethod
  def get_service(*args, **kwargs):
    return FORS.get_instance().get_service(*args, **kwargs)

  def allocate_service(self, service_id):
    """Takes service ID and returns a Service object or None."""
    logger.debug(f"Allocate service {service_id}")
    s = FORS.get_instance().get_service(service_id, refresh_sc=True, refresh_meas=True)
    logger.debug(f"Got service {s}")
    if s is not None:
      # it means that the service is defined in the service cache
      # need to check which node is best suited to host the service
      sn = s.get_node_by_metric() # by default returns node with minimum CPU utilization
      logger.debug(f"Got node {sn}")
      if sn is not None:
        # TODO check if best node is compliant with constraints (e.g.: if min CPU is lower than threshold for allocation)
        if True: # TODO set meaningful condition
          # if so, trigger the requested allocation through FOVIM
          s = FOVIM.get_instance().manage_allocation(service_id=s.get_id(), node_ip=sn.get_ip())
          # TODO get response and return it to user
          # return service with single service node --> 200 OK
          return s
        else:
          # here there are no nodes that are free enough to host this service - it might still be deployable
          # TODO handle this case
          pass
      else:
        # here there are no service nodes registered to this service - it might still be deployable
        # TODO handle this case
        pass
    
    # we get here if the service is not in the service cache or it is but is offered only by busy nodes
    # check if service is deployable (e.g.: "by deploying an APP on a IaaS node"), starting by looking for a source that offers the requested service
    src = self.__get_source_for_service(service_id)
    # check if there is a source that offers the requested service
    if src is not None:
      # check if there is a service to provide the required base (SDP/FVE) for the source
      base_service_id = src["base"]
      base_s = FORS.get_instance().get_service(base_service_id)
      if base_s is not None:
        # here the base service is present in the service cache
        # check if there is a node that is free enough to host the new allocation
        base_sn = base_s.get_node_by_metric()
        if base_sn is not None:
          # TODO check if best node is compliant with constraints (e.g.: if min CPU is lower than threshold for allocation)
          if True: # TODO set meaningful condition
            # TODO if so, deploy the source and allocate service on it --> 201 Created
            s = FOVIM.get_instance().manage_deployment(service_id=service_id, source=src, node_ip=base_sn.get_ip())
            # return service with single service node --> 201 Created
            return s
        else:
          # TODO here there are no more resources for new deployments
          # return service with empty node list --> 503 Service Unavailable
          return forch.Service(id=service_id)

    # TODO here unknown service --> 404 Not Found
    return None


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
    logger.debug(f"Get service list from service cache refresh cache {refresh_sc} refresh meas {refresh_meas}")
    if refresh_sc:
      self.__refresh_service_cache()
    service_list = self.__sc.get_list()
    if refresh_meas:
      for s in service_list:
        s.refresh_measurements()
    return service_list

  def get_service(self, service_id, *, refresh_sc=False, refresh_meas=False):
    try:
      s_list = self.get_service_list(refresh_sc=refresh_sc, refresh_meas=refresh_meas)
      return next(s for s in s_list if s.get_id() == service_id)
    except StopIteration:
      logger.debug(f"Service {service_id} not found")
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
  def manage_allocation(*, service_id, node_ip):
    logger.debug(f"Allocate {service_id} on node {node_ip}")
    # TODO
    # s = FORS.get_instance().get_service(service_id)
    # sn = s.get_node_by_id(node_id)
    s = forch.Service(id=service_id)
    s.add_node(ipv4=node_ip)
    return s

  @staticmethod
  def manage_deployment(*, service_id, node_ip, source):
    logger.debug(f"Deploy {service_id} with {source} on node {node_ip}")
    # TODO
    s = forch.Service(id=service_id)
    s.add_node(ipv4=node_ip)
    return s



### instantiate components

FOB.get_instance()
FORS.get_instance()
FOVIM.get_instance()

### API Resources

class Test(Resource):
  def get(self):
    return {
      "message": f"This component ({Path(__file__).name}) is up!",
      "type": "TEST_OK"
    }

class FogServices(Resource):
  def get(self, s_id=""):
    """Gather list of services and format it in a response."""
    # get list of services
    s_list = FOB.get_instance().get_service_list(refresh_sc=True, refresh_meas=True)
    # format response based on request
    s_id_list = [ s.get_id() for s in s_list ]
    # check if a service was specified
    if s_id:
      if s_id in s_id_list:
        return {
          "message": f"Requested service {s_id} found.",
          # "type": "FOCO_SERV_OK",
          "services": [ s_id ]
        }, 200
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
      }, 200

  def post(self, s_id):
    """Submit request for allocation of a service."""
    s = FOB.get_instance().allocate_service(s_id) # returns Service and code
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
        # TODO find a way to distinguish 200 from 201
        return {
          "message": f"Service {s.get_id()} allocated on node {s.get_node_list()[0]}."
          # "type": "FOCO_SERV_POST"
        }, 200

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