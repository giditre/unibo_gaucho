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

import requests

import forch
forch.set_orchestrator()

logger.debug("IS_ORCHESTRATOR: {}".format(forch.is_orchestrator()))


class Source():
  def __init__(self, *, id, name, description="", locator, base, service, port_list):

    self.id = id
    self.name = name
    self.description = description
    self.base = base
    self.service = service
    self.port_list = port_list
    
  def get_id(self):
    return self.id
  def set_id(self, id) :
    self.id = id

  def get_name(self):
    return self.name
  def set_name(self, name) :
    self.name = name

  def get_description(self):
    return self.description
  def set_description(self, description) :
    self.description = description

  def get_base(self):
    return self.base
  def set_base(self, base) :
    self.base = base

  def get_service(self):
    return self.service
  def set_service(self, service) :
    self.service = service

  def get_port_list(self):
    return self.port_list
  def set_port_list(self, port_list) :
    self.port_list = port_list


class FOB(object):
  __key = object()
  __instance = None

  def __init__(self, *, key=None):
    assert key == self.__class__.__key, "There can only be one {0} object and it can only be accessed with {0}.get_instance()".format(self.__class__.__name__)
    # gather list of available sources (SDP codelets and FVE images)
    # TODO improve loading sources
    with open(str(Path(__file__).parent.joinpath("sources_catalog.json").absolute())) as f:
      sources_dict = json.load(f)
    self.__sources_list = sources_dict["sources"]

  @classmethod
  def get_instance(cls):
    if cls.__instance is None:
      cls.__instance = cls(key=cls.__key)
    return cls.__instance

  @classmethod
  def del_instance(cls):
    if cls.__instance is not None:
      del cls.__instance

  def __get_sources_list(self):
    return self.__sources_list

  def __get_source_for_service(self, service_id, *, priority_list=["FVE", "SDP"]):
    """Finds source that implements requested service"""
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

  def activate_service(self, service_id):
    """Takes service ID and returns a Service object or None."""
    logger.debug(f"Start activating service {service_id}")
    s = FORS.get_instance().get_service(service_id, refresh_sc=True, refresh_meas=True)
    if s is not None:
      # it means that the service is defined in the service cache
      logger.debug(f"Service {s.get_id()} found in cache")
      # need to check which node is best suited to host the service
      sn = s.get_node_by_metric() # by default returns node with minimum CPU utilization
      logger.debug(f"Found node {sn.get_id()} offering {s.get_id()}")
      if sn is not None:
        # TODO check if best node is compliant with constraints (e.g.: if min CPU is lower than threshold for allocation)
        if True: # TODO set meaningful condition
          # if so, trigger the requested allocation through FOVIM
          logger.debug(f"Allocate service {s.get_id()} on node {sn.get_id()}")
          s = FOVIM.get_instance().manage_allocation(service_id=s.get_id(), node_ip=sn.get_ip())
          # TODO get response and return it to user
          # return service with single service node --> 200 OK
          return s
        else:
          # here there are no nodes that are free enough to host this service - it might still be deployable
          logger.debug(f"Nodes offering service {s.get_id()} are too busy")
          # TODO handle this case
          pass
      else:
        # here there are no service nodes associated to this service - it might still be deployable
        logger.debug(f"No nodes offering registered service {s.get_id()}")
        # TODO handle this case - but is it even possible to get here? Because services are registered by nodes offering them
        pass
    
    # we get here if the service is not in the service cache or it is but is offered only by busy nodes
    logger.debug(f"Attempt deployment of service {service_id}")
    # check if service is deployable (e.g.: "by deploying an APP on a IaaS node"), starting by looking for a source that offers the requested service
    src = self.__get_source_for_service(service_id)
    # check if there is a source that offers the requested service
    if src is not None:
      logger.debug(f"Found a source for service {service_id}")
      # check if there is a service that provides the required base (SDP/FVE) for the source
      base_service_id = src["base"]
      base_s = FORS.get_instance().get_service(base_service_id)
      if base_s is not None:
        # here the base service is present in the service cache
        logger.debug(f"Base service {base_s.get_id()} found in cache")
        # check if there is a node that is free enough to host the new allocation
        sn = base_s.get_node_by_metric()
        logger.debug(f"Found node {sn.get_id()} offering {base_s.get_id()}")
        if sn is not None:
          # TODO check if best node is compliant with constraints (e.g.: if min CPU is lower than threshold for allocation)
          if True: # TODO set meaningful condition
            # if so, deploy the source and allocate service on it
            logger.debug(f"Deploy service {service_id} on node {sn.get_id()} on top of base {base_s.get_id()}")
            s = FOVIM.get_instance().manage_deployment(service_id=service_id, source=src, node_ip=sn.get_ip())
            # return service with single service node --> 201 Created
            return s
        else:
          # here there are no more resources for new deployments
          logger.debug(f"Nodes offering base service {base_s.get_id()} are too busy")
          # return service with empty node list --> 503 Service Unavailable
          return forch.Service(id=service_id)

    # here unknown service --> 404 Not Found
    logger.debug(f"Unknown service {service_id}")
    return None

  def deactivate_service(self, service_id):
    logger.debug(f"Start deactivating service {service_id}")
    # TODO get list of nodes
    FOVIM.get_instance().manage_destruction(service_id=service_id)


class FORS(object):
  __key = object()
  __instance = None

  def __init__(self, *, key=None):
    assert key == self.__class__.__key, "There can only be one {0} object and it can only be accessed with {0}.get_instance()".format(self.__class__.__name__)
    self.__sc = forch.ServiceCache()

  @classmethod
  def get_instance(cls):
    if cls.__instance is None:
      cls.__instance = cls(key=cls.__key)
    return cls.__instance

  @classmethod
  def del_instance(cls):
    if cls.__instance is not None:
      del cls.__instance

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

  @classmethod
  def del_instance(cls):
    if cls.__instance is not None:
      del cls.__instance

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
    logger.debug(f"Deploy {service_id} on node {node_ip} with source {source}")
    
    response = requests.post(f"http://{node_ip}:6001/services/{service_id}",
      json={"base": source["base"], "image": source["uri"]}
      )
    
    response_code = response.status_code
    if response_code == 201:
      response_json = response.json()
      s = forch.Service(id=service_id)
      
      if len(source["ports"]) == 0:
        s.add_node(ipv4=node_ip)
      else:
        for port in source["ports"]:
          s.add_node(ipv4=node_ip, port=int(response_json["port_mappings"][port]))
      
      return s
    else:
      # TODO handle this case
      return None

  @staticmethod
  def manage_destruction(*, service_id, node_ip):
    logger.debug(f"Destroy {service_id} on node {node_ip}")
    
    response = requests.delete(f"http://{node_ip}:6001/services/{service_id}")

    return response.json(), response.status_code


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
    s = FOB.get_instance().activate_service(s_id) # returns Service and code
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
        sn = s.get_node_list()[0]
        # TODO find a way to distinguish 200 from 201
        return {
          "message": f"Service {s.get_id()} available on node {sn.get_id()}",
          "node_ip": str(sn.get_ip()),
          "node_port": sn.get_port()
          # "type": "FOCO_SERV_POST"
        }, 200

  def delete(self, s_id=""):
    """Submit request for deallocation of services."""
    FOB.get_instance().activate_service(s_id)

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

  ### instantiate components

  FOB.get_instance()
  FORS.get_instance()
  FOVIM.get_instance()

  ### REST API

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
    logger.info("Cleanup after interruption")
    FOB.del_instance()
    FORS.del_instance()
    FOVIM.del_instance()