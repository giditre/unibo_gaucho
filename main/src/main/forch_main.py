import logging
from logging.config import fileConfig
from pathlib import Path
fileConfig(str(Path(__file__).parent.joinpath("logging.ini")))
logger = logging.getLogger(__name__)
logger.info(f"Load {__name__} with {logger}")

import json

import flask
from flask_restful import Resource, Api

import requests

import forch
forch.set_orchestrator()

logger.debug(f"Running as orchestrator? {forch.is_orchestrator()}")

# TODO G: move this to FOVIM if not used by anything else (the usage in FOB should be moved to FOVIM too)
def http_request(endpoint, *, method="GET", request_json_data=None):
  assert method in ["GET", "POST", "PUT", "DELETE"], "Invalid method!"
  url = f"http://{endpoint}"
  logger.debug(f"HTTP {method} - URL {url} - JSON: {json.dumps(request_json_data, indent=2)}")
  response = None
  try:
    if method == "GET":
      response = requests.get(url)
    elif method == "POST":
      response = requests.post(url, json=request_json_data)
    elif method == "PUT":
      response = requests.put(url, json=request_json_data)
    elif method == "DELETE":
      response = requests.delete(url)
  except requests.exceptions.ConnectionError as ce:
    logger.warning(f"Failed to {method} {url} {ce}")
    return None, 500
  resp_code = response.status_code
  resp_json = response.json()
  logger.debug(f"Response code {resp_code} - JSON body {json.dumps(resp_json, indent=2)}")
  return resp_json, response.status_code

def http_get(endpoint):
  return http_request(endpoint, method="GET")

def http_post(endpoint, request_json_data):
  return http_request(endpoint, method="POST", request_json_data=request_json_data)

def http_put(endpoint, request_json_data):
  return http_request(endpoint, method="PUT", request_json_data=request_json_data)
  
def http_delete(endpoint):
  return http_request(endpoint, method="DELETE")

###

from functools import wraps

def debug_markers(f):
  @wraps(f)
  def wrapper(*args, **kwargs):
    logger.debug(f"marker start {f.__qualname__}")
    result = f(*args, **kwargs)
    logger.debug(f"marker end {f.__qualname__}")
    return result
  return wrapper

###

class Source():

  def __init__(self, *, name, base, service, port_list, description=None):
    self.__id = id
    self.__name = name
    self.__base = base
    self.__service = service
    self.__port_list = port_list
    self.__description = description
    
  def get_id(self):
    return self.__id
  def set_id(self, id) :
    self.__id = id

  def get_name(self):
    return self.__name
  def set_name(self, name) :
    self.__name = name

  def get_base(self):
    return self.__base
  def set_base(self, base) :
    self.__base = base

  def get_service(self):
    return self.__service
  def set_service(self, service) :
    self.__service = service

  def get_port_list(self):
    return self.__port_list
  def set_port_list(self, port_list) :
    self.__port_list = port_list

  def get_description(self):
    return self.__description
  def set_description(self, description) :
    self.__description = description

class FOM(object):

  __key = object()
  __instance = None

  def __init__(self, *, key=None):
    assert key == self.__class__.__key, "There can only be one {0} object and it can only be accessed with {0}.get_instance()".format(self.__class__.__name__)

    # define list of available sources (SDP codelets and FVE images)
    self.__source_list = []

    # define list of active services - active means allocated or deployed, not just available
    self.__active_service_list = []

    # define list of projects
    self.__project_list = []

  @classmethod
  def get_instance(cls):
    if cls.__instance is None:
      cls.__instance = cls(key=cls.__key)
    return cls.__instance

  @classmethod
  def del_instance(cls):
    if cls.__instance is not None:
      del cls.__instance

  def __get_source_list(self):
    return self.__source_list

  def __set_source_list(self, src_list):
    assert all( isinstance(s, Source) for s in src_list ), "All elements must be Source objects!"
    self.__source_list = src_list

  def load_source_list_from_json(self, json_file_name):

    # TODO check if file name is already absolute and if it exists
    with open(str(Path(__file__).parent.joinpath(json_file_name).absolute())) as f:
      sources_dict = json.load(f)
    
    src_list = [ Source(name=src["name"], base=src["base"], service=src["service"], port_list=src["ports"])
      for src in sources_dict["sources"] ]
    # equivalent to
    # for src in sources_dict["sources"]:
    #   src_list.append( Source(name=src["name"], base=src["base"], service=src["service"], port_list=src["ports"]))

    self.__set_source_list(src_list)

  def __search_source_for_service(self, service_id, *, priority_list=["FVE", "SDP"]):
    """Searches source that implements requested service"""
    for p in priority_list:
      try:
        return next(src for src in self.__get_source_list() if src.get_service() == service_id and p in src.get_base())
      except StopIteration:
        continue
    logger.debug(f"No source found for service {service_id}")
    return None

  def get_active_service_list(self):
    return self.__active_service_list

  def __set_active_service_list(self, active_service_list):
    assert all( isinstance(s, forch.ActiveService) for s in active_service_list ), "All elements must be ActiveService objects!"
    self.__active_service_list = active_service_list

  def get_project_list(self):
    return self.__project_list

  def set_project_list(self, project_list):
    assert all( isinstance(s, forch.Project) for s in project_list ), "All elements must be Project objects!"
    self.__project_list = project_list

  def get_project_by_name(self, project_name):
    for p in self.get_project_list():
      if p.get_name() == project_name:
        return p
    return None

  def update_active_service_list(self, active_service):
    active_service_list = self.get_active_service_list()
    if active_service not in active_service_list:
      active_service_list.append(active_service)
      self.__set_active_service_list(active_service_list)

  def find_active_services(self, *args, **kwargs):
    """Find currently active services on known nodes"""
    service_list = self.get_service_list(*args, **kwargs)
    for s in service_list:
      for sn in s.get_node_list():
        node_ip = sn.get_ip()
        # query node
        # TODO do this through FOVIM
        resp_json, resp_code = http_get(f"{node_ip}:{forch.get_fog_node_main_port()}/services")
        if resp_json is None:
          logger.warning(f"Failed to get services from node {sn.get_id()} at {node_ip}")
          continue
        sn_service_list = resp_json["services"]
        for s_dict in sn_service_list: # every element is expected to be a dict with parameters of ActiveService
          s_dict.update(node_ip=node_ip)
          active_s = forch.ActiveService(**s_dict)
          logger.info(f"Found active service {active_s.get_service_id()}") 
          self.update_active_service_list(active_s)

  @staticmethod
  def get_service_list(*args, **kwargs):
    return FOA.get_instance().get_service_list(*args, **kwargs)

  @staticmethod
  def get_service(*args, **kwargs):
    return FOA.get_instance().get_service(*args, **kwargs)

  @debug_markers
  def activate_service(self, service_id, *, project):
    """Takes service ID and returns an ActiveService object or None."""
    logger.info(f"Start activating instance of service {service_id}")
    s = FOA.get_instance().get_service(service_id, refresh_sc=True, refresh_meas=True)
    if s is not None:
      # it means that the service is defined in the service cache
      logger.info(f"Service {s.get_id()} found in cache")
      # need to check which node is best suited to host the service
      sn = s.get_node_by_metric(forch.MetricType.CPU, check="min") # (by default) returns node with minimum CPU utilization
      logger.info(f"Found node {sn.get_id()} offering {s.get_id()}")
      if sn is not None:
        # TODO check if best node is compliant with constraints (e.g.: if min CPU is lower than threshold for allocation)
        sn_metric = sn.get_metric_by_type(forch.MetricType.CPU)
        logger.info(f"Node {sn.get_id()}: {forch.MetricType.CPU.value} {sn_metric.get_value()}{sn_metric.get_unit()}")
        if float(sn_metric.get_value()) < 90: # TODO avoid hardcoding threshold
          # if so, trigger the requested allocation through FOVIM
          logger.info(f"Allocate service {s.get_id()} on node {sn.get_id()}")
          active_s = FOVIM.get_instance().manage_allocation(service_id=s.get_id(), node_ip=sn.get_ip())
          # TODO verify response is an ActiveService with single service node and return it to user --> 200 OK

          # just before returning, update active service list
          self.update_active_service_list(active_s)

          return active_s
        else:
          # here there are no nodes that are free enough to host this service - it might still be deployable
          logger.info(f"Nodes offering service {s.get_id()} are too busy")
          # TODO handle this case
          pass
      else:
        # here there are no service nodes associated to this service - it might still be deployable
        logger.info(f"No nodes offering registered service {s.get_id()}")
        # TODO handle this case - but is it even possible to get here? Because services are registered by nodes offering them
        pass
    
    # we get here if the service is not in the service cache or it is but is offered only by busy nodes
    logger.info(f"Attempt deployment of service {service_id}")
    # check if service is deployable (e.g.: "by deploying an APP on a IaaS node"), starting by looking for a source that offers the requested service
    src = self.__search_source_for_service(service_id)
    # check if there is a source that offers the requested service
    if src is not None:
      logger.info(f"Found a source for service {service_id}")
      # check if there is a service that provides the required base (SDP/FVE) for the source
      base_service_id = src.get_base()
      base_s = FOA.get_instance().get_service(base_service_id)
      if base_s is not None:
        # here the base service is present in the service cache
        logger.info(f"Base service {base_s.get_id()} found in cache")
        # check if there is a node that is free enough to host the new allocation
        sn = base_s.get_node_by_metric()
        logger.info(f"Found node {sn.get_id()} offering {base_s.get_id()}")
        if sn is not None:
          # check if best node is compliant with constraints (e.g.: if min CPU is lower than threshold for allocation)
          sn_metric = sn.get_metric_by_type(forch.MetricType.CPU)
          logger.info(f"Node {sn.get_id()}: {forch.MetricType.CPU.value} {sn_metric.get_value()}{sn_metric.get_unit()}")
          if float(sn_metric.get_value()) < 90: # TODO avoid hardcoding threshold
            # if so, deploy the source and allocate service on it
            logger.info(f"Deploy service {service_id} on node {sn.get_id()} on top of base {base_s.get_id()}")
            active_s = FOVIM.get_instance().manage_deployment(service_id=service_id, project=project, source=src, node_ip=sn.get_ip())
            # verify response is a service with single service node and return it to user --> 201 Created
            assert isinstance(active_s, forch.ActiveService) and len(active_s.get_node_list()) == 1, ""
            # just before returning, update active service list
            self.update_active_service_list(active_s)
            return active_s
        
        # here there are no more resources for new deployments
        logger.info(f"Nodes offering base service {base_s.get_id()} are too busy")
        # return service with empty node list --> 503 Service Unavailable
        return forch.ActiveService(service_id=service_id)

    # here unknown service --> 404 Not Found
    logger.info(f"Unknown service {service_id}")
    return None

  @debug_markers
  def deactivate_service(self, service_id):
    logger.info(f"Deactivating instances of service {service_id}")
    # find relevant entry or entries in active services
    for active_service in self.get_active_service_list():
      if active_service.get_service_id() == service_id:
        # # use base_service_id to get Service object in order to get id of node where service is deployed
        # base_s = self.get_service(active_service.get_base_service_id())
        # sn = base_s.get_node_by_id(active_service.get_node_id())
        sn = active_service.get_node_by_id(active_service.get_node_id())
        # destroy service on node
        FOVIM.get_instance().manage_destruction(service_id=service_id, node_ip=sn.get_ip())

  @debug_markers
  def deactivate_all_services(self):
    logger.info(f"Deactivating all services")
    # find relevant entry or entries in active services
    for active_service in self.get_active_service_list():
      self.deactivate_service(active_service.get_service_id())

  @staticmethod
  def check_faas():

    faas_list = []

    s_list = FOM.get_instance().get_service_list(refresh_sc=True, refresh_meas=True)

    for item in FOM.get_instance().__get_source_list():
    
      if item.get_service()[0:3] == 'LAF' and item.get_service() not in [s.get_id() for s in s_list]:

        faas_list.append({'s_id': item.get_service(), 's_ipv4': '192.168.64.117:6000', 's_path': f'/faasservices/{item.get_service()}'})

    return faas_list

class FOGW(object):

  __key = object()
  __instance = None

  def __init__(self, *, key=None):

    assert key == self.__class__.__key, f"There can only be one {self.__class__.__name__} object and it can only be accessed with {self.__class__.__name__}.get_instance()"
  
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
  def get_service_list(*args, **kwargs):

    return FOM.get_instance().get_service_list(*args, **kwargs)

  @staticmethod
  def get_project_by_name(project_name):

    return FOM.get_instance().get_project_by_name(project_name)

  @staticmethod
  def activate_service(service_id, *, project):

    return FOM.get_instance().activate_service(service_id, project=project)

  @staticmethod
  def check_faas():

    return FOM.get_instance().check_faas()

  @staticmethod
  def deactivate_service(service_id):

    FOM.get_instance().deactivate_service(service_id)

  @staticmethod
  def deactivate_all_services():

    FOM.get_instance().deactivate_all_services()

class FOA(object):

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

  @debug_markers
  def get_service_list(self, *, refresh_sc=False, refresh_meas=False):

    logger.debug(f"Get service list from service cache refresh cache {refresh_sc} refresh meas {refresh_meas}")

    if refresh_sc:

      self.__refresh_service_cache()

    service_list = self.__sc.get_list()

    if refresh_meas:

      for s in service_list:

        s.refresh_measurements()

    return service_list

  @debug_markers
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
  @debug_markers
  def manage_allocation(*, service_id, node_ip):
    logger.debug(f"Allocate {service_id} on node {node_ip}")
    # TODO interact with the node (PUT) and ensure allocation of service (allocation is not deployment)
    # s = FORS.get_instance().get_service(service_id)
    # sn = s.get_node_by_id(node_id)
    resp_json, resp_code = http_put(f"{node_ip}:{forch.get_fog_node_main_port()}/services/{service_id}", {"test": "dummy"})
    # TODO check response code and handle errors
    if resp_json is None:
      logger.error(f"Failed to allocate service on node at {node_ip}")
      # TODO handle error
    # TODO check resp code and act accordingly
    logger.debug("Allocation response: {}".format(json.dumps(resp_json)))
    active_s = forch.ActiveService(service_id=service_id)
    active_s.add_node(ipv4=node_ip, port=int(resp_json["port"]))
    return active_s

  @staticmethod
  @debug_markers
  def manage_deployment(*, service_id, node_ip, source, project):
    """Manages deployment of service on node based on source.
    Returns: ActiveService or None
    """
    logger.debug(f"Deploy {service_id} on node {node_ip} with source {source}")
    
    base_service_id = source.get_base()

    if base_service_id == forch.FogServiceID.DOCKER.value:
      # build JSON
      request_json = dict(base=source.get_base(), image=source.get_name())
      # extract additional project configurations for this instance
      # then relate them to Docker, and serialize them into the JSON of the POST
      if project.get_instance_configuration_dict():
        instance_conf_dict = { forch.DockerContainerConfiguration[conf_name].value: conf_value
          for conf_name, conf_value in project.get_instance_configuration_dict().items() }
        request_json["instance_conf"] = instance_conf_dict # TODO avoid hardcoding string
        # network configuration
        if forch.InstanceConfiguration.ATTACH_TO_NETWORK.value in project.get_instance_configuration_dict():
          network_conf_dict = { forch.DockerNetworkConfiguration[conf_name].value: conf_value
          for conf_name, conf_value in project.get_network_configuration_dict().items() }
          request_json["network_conf"] = network_conf_dict # TODO avoid hardcoding string
      # send deployment request to node
      logger.debug("Deployment request: {}".format(json.dumps(request_json)))
      response_json, response_code = http_post(f"{node_ip}:{forch.get_fog_node_main_port()}/services/{service_id}", request_json)
      if response_code == 201:
        logger.debug("Deployment response: {}".format(json.dumps(response_json)))
        active_s = forch.ActiveService(service_id=service_id, base_service_id=base_service_id,
          instance_name=response_json["name"], instance_ip=response_json["ip"])
        src_port_list = source.get_port_list()
        if len(src_port_list) == 0:
          active_s.add_node(ipv4=node_ip)
        elif len(src_port_list) == 1:
          port = src_port_list[0]
          active_s.add_node(ipv4=node_ip, port=int(response_json["port_mappings"][port]))
        else:
          # TODO handle this case: what's better? Add a separate ServiceNode per port of the service, or a single ServiceNode with multiple ports? (in the latter case, probably need to modify ServiceNode)
          raise NotImplementedError
          # for port in src_port_list:
          #   active_s.add_node(ipv4=node_ip, port=int(response_json["port_mappings"][port]))
        return active_s
      else:
        # TODO handle case of wrong or unexpected status code of response
        return None
    else:
      # TODO handle case of unknown base_service_id -- is it even possible?
      pass

  @staticmethod
  @debug_markers
  def manage_destruction(*, service_id, node_ip):
    logger.debug(f"Destroy {service_id} on node {node_ip}")
    
    response_json, response_code = http_delete(f"{node_ip}:{forch.get_fog_node_main_port()}/services/{service_id}")
    # TODO avoid returning this directly, but process it and return a single value, maybe the service id
    return response_json, response_code


### API Resources

class Test(Resource):
  def get(self):
    return {
      "message": f"This component ({Path(__file__).name}) is up!",
      # "type": "TEST_OK"
    }

class FaaSServices(Resource):

  def post(self, s_id):

    project = FOGW.get_instance().get_project_by_name('FaaS')

    active_s = FOGW.get_instance().activate_service(s_id, project=project) # returns ActiveService
    if active_s is None:
      # service not found
      return {
          "message": f"Requested service {s_id} not found."
          # "type": "FOCO_SERV_POST",
          # "services": []
        }, 404
    
    if isinstance(active_s, forch.ActiveService):
      assert len(active_s.get_node_list()) in [0,1], "Too many ServiceNodes!"
      if active_s.get_node_list() is None or len(active_s.get_node_list()) == 0:
        return {
        "message": f"Service {active_s.get_id()} unavailable."
        # "type": "FOCO_SERV_POST"
        }, 503
      elif len(active_s.get_node_list()) == 1:
        sn = active_s.get_node_by_id(active_s.get_node_id())
        return {
          "message": f"Service {active_s.get_id()} available on node {sn.get_id()}",
          "node_ip": str(sn.get_ip()),
          "instance_name": str(active_s.get_instance_name()),
          "instance_ip": str(active_s.get_instance_ip()),
          "node_port": sn.get_port()
          # "type": "FOCO_SERV_POST"
        }, 307
    else:
      # TODO handle case
      pass

class FogServices(Resource):

  def get(self, s_id=""):
    """Gather list of services and format it in a response."""
    # get list of services
    s_list = FOGW.get_instance().get_service_list(refresh_sc=True, refresh_meas=True)
    # check faas services in sources
    faas_list = FOGW.get_instance().check_faas()
    # create list of service IDs
    s_id_list = [ s.get_id() for s in s_list ]
    # create list of faas service IDs 
    faas_id_list = [ fs['s_id'] for fs in faas_list ]
    for serv in s_list:
      if serv.get_id().startswith('LAF'):
        s_list.remove(serv)
        # newfaas = {'s_id': serv.get_id(), 's_ipv4': f'{serv.get_node_list()[0].get_ip()}:{serv.get_node_list()[0].get_port()}', 's_path': f'/faasservices/{serv.get_id()}'}
        faas_list.append({'s_id': serv.get_id(), 's_ipv4': f'{serv.get_node_list()[0].get_ip()}:{serv.get_node_list()[0].get_port()}', 's_path': '/trn'})
    # check if a service was specified
    if s_id:
      if s_id in s_id_list:
        return {
          "message": f"Requested service {s_id} found.",
          # "type": "FOCO_SERV_OK",
          "services": [ s_id ]
        }, 200
      elif s_id in faas_id_list:
        fs = {}
        for item in faas_list:
          if s_id == item['s_id']:
            fs.update(item)
        return {
          "message": f"Requested service {s_id} found.",
          # "type": "FOCO_SERV_OK",
          "faasservices": [ f"{s_id} {item['s_ipv4']}{item['s_path']}" ]
        }, 200
      else:
        return {
          "message": f"Requested service {s_id} not found.",
          # "type": "FOCO_SERV_LIST",
          "services": []
        }, 404
    else:
      return {
        "message": f"Found {len(s_list)+len(faas_list)} service(s).",
        # "type": "FOCO_SERV_LIST",
        "services": [ s.get_id() for s in s_list ],
        "faasservices": [ f"{item['s_id']} {item['s_ipv4']}{item['s_path']}" for item in faas_list ]
      }, 200

  def post(self, s_id):
    """Submit request for activation of a service."""

    request_json = flask.request.get_json(force=True)

    # retrieve project name from request JSON, or if no project is specified, default to a default name
    if "project" in request_json: # TODO avoid hardcoding strings
      project_name = request_json["project"]
    else:
      return {
          "message": f"Must specify project name" 
          # "type": "FOCO_SERV_POST",
          # "services": []
        }, 404
    
    # find Project instance in FOB
    project = FOGW.get_instance().get_project_by_name(project_name)
    if project is None:
      # project not found
      return {
          "message": f"Project {project_name} not found."
          # "type": "FOCO_SERV_POST",
          # "services": []
        }, 404

    active_s = FOGW.get_instance().activate_service(s_id, project=project) # returns ActiveService
    if active_s is None:
      # service not found
      return {
          "message": f"Requested service {s_id} not found."
          # "type": "FOCO_SERV_POST",
          # "services": []
        }, 404
    
    if isinstance(active_s, forch.ActiveService):
      assert len(active_s.get_node_list()) in [0,1], "Too many ServiceNodes!"
      if active_s.get_node_list() is None or len(active_s.get_node_list()) == 0:
        return {
        "message": f"Service {active_s.get_id()} unavailable."
        # "type": "FOCO_SERV_POST"
        }, 503
      elif len(active_s.get_node_list()) == 1:
        # distinguish 200 from 201 by checking if service_id and base_service_id are the same
        if active_s.get_service_id() == active_s.get_base_service_id():
          # allocation
          sn = active_s.get_node_by_id(active_s.get_node_id())
          return {
            "message": f"Service {active_s.get_id()} available on node {sn.get_id()}",
            "node_ip": str(sn.get_ip()),
            "instance_name": str(active_s.get_instance_name()),
            "instance_ip": str(active_s.get_instance_ip()),
            "node_port": sn.get_port()
            # "type": "FOCO_SERV_POST"
          }, 200
        else:
          # deployment
          sn = active_s.get_node_by_id(active_s.get_node_id())
          return {
            "message": f"Service {active_s.get_id()} available on node {sn.get_id()}",
            "node_ip": str(sn.get_ip()),
            "instance_name": str(active_s.get_instance_name()),
            "instance_ip": str(active_s.get_instance_ip()),
            "node_port": sn.get_port()
            # "type": "FOCO_SERV_POST"
          }, 201
    else:
      # TODO handle case
      pass

  def delete(self, s_id=""):
    """Submit request for deactivation of services."""
    if s_id:
      FOGW.get_instance().deactivate_service(s_id)
      # TODO check if operation was successful
      return {
          "message": f"Service {s_id} deactivated",
          # "node_ip": str(sn.get_ip()),
          # "node_port": sn.get_port(),
          # "type": "FOCO_SERV_POST"
        }, 200
    else:
      FOGW.get_instance().deactivate_all_services()
      # TODO check if operation was successful
      return {
          "message": f"All services deactivated",
          # "node_ip": str(sn.get_ip()),
          # "node_port": sn.get_port(),
          # "type": "FOCO_SERV_POST"
        }, 200

if __name__ == "__main__":

  ### argument parser

  # import argparse

  # default_address = "127.0.0.1"
  # default_port = 6000

  # parser = argparse.ArgumentParser()
  # parser.add_argument("-a", "--address", help=f"This component's IP address, default: {default_address}",
  #   nargs="?", default=default_address)
  # parser.add_argument("-p", "--port", help=f"This component's TCP port, default: {default_port}", type=int,
  #   nargs="?", default=default_port)
  # parser.add_argument("-d", "--debug", help="Run in debug mode", action="store_true", default=False)
  # args = parser.parse_args()

  local_config = forch.get_local_config(Path(__file__).parent.joinpath("main.ini").absolute())
  logger.debug(f"Config: {dict(local_config.items())}")

  ### instantiate components

  FOM.get_instance()

  FOA.get_instance()

  FOVIM.get_instance()

  ### perform preliminary operations

  FOM.get_instance().load_source_list_from_json(str(Path(__file__).parent.joinpath(local_config["sources_json"]).absolute()))
  FOM.get_instance().find_active_services(refresh_sc=True) # TODO add configuration flag for this
  preexisting_active_service_list = FOM.get_instance().get_active_service_list()
  if preexisting_active_service_list:
    logger.debug(f"Found {len(preexisting_active_service_list)} pre-existing service(s): {[(s.get_service_id(), s.get_node_id(), s.get_instance_name()) for s in preexisting_active_service_list]}")

  # project configurations

  # TODO add configuration file for this

  FOM.get_instance().set_project_list([
    forch.Project("FaaS"),
    forch.Project("default"),
    forch.Project("test-project",
      instance_configuration_dict={
        forch.InstanceConfiguration.DETACH.value: True,
        forch.InstanceConfiguration.KEEP_STDIN_OPEN.value: True,
        forch.InstanceConfiguration.ALLOCATE_TERMINAL.value: True,
        forch.InstanceConfiguration.ATTACH_TO_NETWORK.value: "test-net",
        forch.InstanceConfiguration.FORWARD_ALL_PORTS.value: True
      },
      network_configuration_dict={
        forch.NetworkConfiguration.BRIDGE_NAME.value: "bridge-test",
        forch.NetworkConfiguration.IPv4_SUBNET.value: "192.168.111.0/24",
        forch.NetworkConfiguration.IPv4_RANGE.value: "192.168.111.128/25",
        forch.NetworkConfiguration.IPv4_GATEWAY.value: "192.168.111.10"
      }
    ),
    forch.Project("mec-project",
      instance_configuration_dict={
        forch.InstanceConfiguration.DETACH.value: True,
        forch.InstanceConfiguration.KEEP_STDIN_OPEN.value: True,
        forch.InstanceConfiguration.ALLOCATE_TERMINAL.value: True,
        forch.InstanceConfiguration.ATTACH_TO_NETWORK.value: "mec-net",
        forch.InstanceConfiguration.DNS_SERVER.value: ["10.15.105.11"],
        forch.InstanceConfiguration.FORWARD_ALL_PORTS.value: True,
        forch.InstanceConfiguration.ENVIRONMENT_VARIABLE.value: {
          "INFRA": "fog",
          "MEC_BASE": "http://mec-platform.mec.mec.host"
        }
      },
      network_configuration_dict={
        forch.NetworkConfiguration.BRIDGE_NAME.value: "bridge-mec",
        forch.NetworkConfiguration.IPv4_SUBNET.value: "172.30.30.0/24",
        forch.NetworkConfiguration.IPv4_GATEWAY.value: "172.30.30.254"
      }
    )
  ])

  ### REST API

  app = flask.Flask(__name__)

  @app.before_request
  def before():
    logger.debug("marker start {} {}".format(flask.request.method, flask.request.path))

  @app.after_request
  def after(response):
    logger.debug("marker end {} {}".format(flask.request.method, flask.request.path))
    return response  

  api = Api(app)
  api.add_resource(Test, '/test')
  api.add_resource(FogServices, '/services', '/services/<s_id>')
  api.add_resource(FaaSServices, '/faasservices/<s_id>')

  try:
    app.run(host=local_config.get("address"),
        port=local_config.getint("forch_port"),
        debug=local_config.getboolean("debug"))
  except KeyboardInterrupt:
    pass
  finally:
    logger.info("Cleanup after interruption")
    FOM.del_instance()
    FOA.del_instance()
    FOVIM.del_instance()