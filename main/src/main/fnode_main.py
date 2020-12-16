import logging
from logging.config import fileConfig
from pathlib import Path
fileConfig(str(Path(__file__).parent.joinpath("logging.ini")))
logger = logging.getLogger(__name__)
logger.info(f"Load {__name__} with {logger}")

from ipaddress import IPv4Address
from time import time
import multiprocessing

import flask
from flask_restful import Resource, Api

import docker

import forch
logger.debug("IS_ORCHESTRATOR: {}".format(forch.is_orchestrator()))


class FNVI(object):
  __key = object()
  __instance = None

  def __init__(self, *, key=None):
    assert key == self.__class__.__key, "There can only be one {0} object and it can only be accessed with {0}.get_instance()".format(self.__class__.__name__)

    self.__sa = forch.SLPFactory.create_SA()
    self.__service_list = [] # TODO c'è modo di prendere la lista di servizi registrati sul ServiceAgent?
    self.__active_service_list = []

    self.__ipv4 = None

    self.__docker_client = None

  @classmethod
  def get_instance(cls):
    if cls.__instance is None:
      cls.__instance = cls(key=cls.__key)
    return cls.__instance

  @classmethod
  def del_instance(cls):
    if cls.__instance is not None:
      del cls.__instance

  def __get_SA(self):
    return self.__sa

  def get_service_list(self):
    return self.__service_list

  def __register_service(self, service):
    logger.info(f"Register service {service}")
    self.__get_SA().register_service(service)

  def register_service_list(self):
    s_list = self.get_service_list()
    assert len(s_list) > 0, "Empty service list"
    for service in s_list:
      self.__register_service(service)
    
  def load_service_list_from_json(self, json_file_name):
    ipv4 = None
    if forch.is_orchestrator():
      ipv4 = IPv4Address("127.0.0.1")
    else:
      ipv4 = self.get_ipv4()
    
    assert ipv4 is not None, "Must set an IP address for this node first, using .set_ipv4(ipv4)"

    self.__service_list = forch.Service.create_services_from_json(json_file_name=json_file_name, ipv4=ipv4)

  def get_active_service_list(self):
    return self.__active_service_list

  def __set_active_service_list(self, active_service_list):
    assert all( isinstance(s, forch.ActiveService) for s in active_service_list ), "All elements must be ActiveService objects!"
    self.__active_service_list = active_service_list

  def update_active_service_list(self, active_service):
    active_service_list = self.get_active_service_list()
    if active_service not in active_service_list:
      active_service_list.append(active_service)
      self.__set_active_service_list(active_service_list)

  def find_active_services(self):
    # find pre-existing services
    # cycle over known base services
    for base_service_id in [forch.FogServiceID.DOCKER.value]:
      if base_service_id == forch.FogServiceID.DOCKER.value:
        # Docker-specific
        for cont_s_id in self.list_containerized_services_docker():
          logger.debug(f"Found active service {cont_s_id} base {forch.FogServiceID.DOCKER.value}")
          self.update_active_service_list(forch.ActiveService(service_id=cont_s_id, base_service_id=forch.FogServiceID.DOCKER.value))
      elif base_service_id == "FVExxx":
        pass
      else:
        pass

  def get_ipv4(self):
    return self.__ipv4

  def set_ipv4(self, ipv4):
    if isinstance(ipv4, str):
      ipv4 = IPv4Address(ipv4)
    assert isinstance(ipv4, IPv4Address), "Parameter ipv4 must be an IPv4Address object!"
    self.__ipv4 = ipv4

  def destroy_service(self, service_id):
    """Returns ID of destroyed service"""
    # get relevant instance of ActiveService
    # TODO move this search to a function, handling non-existent service ?
    active_s = next( s for s in self.get_active_service_list() if s.get_id() == service_id )
    # TODO avoid hardcoded FVE SDP APP
    if service_id.startswith("FVE"):
      # TODO deallocate
      pass
    else:
      # check if service_id == base_service_id, meaning service is allocated, else service is deployed
      
      base_service_id = active_s.get_base_service_id()
      if service_id == base_service_id:
        # TODO deallocate
        pass
      else:
        if base_service_id == forch.FogServiceID.DOCKER.value:
          return self.destroy_service_docker(service_id)
        elif base_service_id == "FVExxx":
          pass
        else:
          pass

  def destroy_all_services(self):
    """Returns list of IDs of destroyed services"""
    return [ self.destroy_service(active_s.get_service_id()) for active_s in self.get_active_service_list() ]
  
  # Docker methods

  def __get_docker_client(self):
    if self.__docker_client is None:
      self.__docker_client_init()
    return self.__docker_client

  def __docker_client_init(self):
    self.__docker_client = docker.from_env()
  
  def docker_client_test(self):
    return self.__get_docker_client().ping()

  def docker_network_list(self, *args, **kwargs):
    return self.__get_docker_client().networks.list(*args, **kwargs)

  def docker_network_exists(self, network_name):
    net_list = self.docker_network_list()
    for net in net_list:
      if net.name == network_name:
        return True
    return False

  def docker_network_create_with_bridge(self, network_name, *,
    bridge_name=None, bridge_address=None, subnet=None, dhcp_range=None):

    if self.docker_network_exists(network_name):
      logger.warning(f"Network with name {network_name} already exists.")
      return None
    
    if bridge_name is None:
      bridge_name = f"br-{network_name}"

    ipam_config = None
    if bridge_address is not None or subnet is not None or dhcp_range is not None:

      assert IPv4Address(bridge_address), "Must provide a valid IPv4 address in CIDR notation!"
      assert IPv4Address(subnet), "Must provide a valid IPv4 subnet in CIDR notation!"
      assert IPv4Address(dhcp_range), "Must provide a valid IPv4 subnet in CIDR notation!"

      ipam_config = docker.types.IPAMConfig( pool_configs=[ docker.types.IPAMPool(
        subnet=subnet, iprange=dhcp_range, gateway=bridge_address)
        ])

    return self.__get_docker_client().networks.create(name=network_name,
      driver="bridge", options={"com.docker.network.bridge.name":bridge_name},
      ipam=ipam_config
      )
  
  def docker_network_prune(self):
    return self.__get_docker_client().networks.prune()
    
  def docker_image_is_cached(self, image_name):
    return len(self.__get_docker_client().images.list(name=image_name)) > 0

  def docker_image_pull(self, image_name, *, tag="latest"):
    if not self.docker_image_is_cached(image_name):
      logger.info(f"Need to pull image {image_name}")
      try:
        self.__get_docker_client().images.pull(image_name, tag=tag)
      except docker.errors.ImageNotFound:
        logger.error(f"Cannot pull image {image_name}: image not found!")
        return None
    return self.__get_docker_client().images.get(image_name)

  def docker_image_prune(self):
    self.__get_docker_client().images.prune()

  def docker_container_list(self, *args, **kwargs):
    return self.__get_docker_client().containers.list(*args, **kwargs)

  def docker_container_run(self, image_name, **kwargs):
    img = self.docker_image_pull(image_name)
    if img is None:
      return None
    logger.info(f'Run container {kwargs["name"]}')
    return self.__get_docker_client().containers.run(image_name, **kwargs)

  def docker_container_prune(self):
    logger.debug('Prune containers')
    r = self.__get_docker_client().containers.prune()
    deleted_list = r["ContainersDeleted"] if r["ContainersDeleted"] else list()
    logger.info(f"Pruned {len(deleted_list)} container(s)")
    return deleted_list

  def __generate_container_name(self, service_id, image_name):
    container_name = "_".join([
      service_id,
      image_name.replace("/", "-").replace(":", "-"),
      str(int(time()*1000)) # or '{0:%Y%m%d-%H%M%S-%f}'.format(datetime.now())
      ])
    # check length (limit imposed by hostname field)
    assert len(container_name) < 64, f"Name {container_name} is longer than 63 chars"
    # check there is no other container with this name
    assert container_name not in [ c.name for c in self.docker_container_list() ], f"Name {container_name} already in use by container {self.__get_docker_client().containers.get(container_name)}"
    return container_name

  def list_containerized_services_docker(self, *, service_type_list=["APP", "SDP"]):
    return list(set([ c.name.split("_")[0] for c in self.docker_container_list()
      if any(c.name.startswith(service_type) for service_type in service_type_list) ]))

  def deploy_service_docker(self, service_id, image_name, **kwargs):

    container_name = self.__generate_container_name(service_id, image_name)

    logger.debug(f"Deploy service {service_id} with container {container_name} using image {image_name}")

    # container = self.docker_container_run(image_name, name=container_name, hostname=container_name, detach=True, stdin_open=True, tty=True, publish_all_ports=True, command=None, entrypoint=None)

    container = self.docker_container_run(image_name, name=container_name, hostname=container_name, **kwargs)

    if container is None:
      return None

    # just before returning, update active service list
    self.update_active_service_list(forch.ActiveService(service_id=service_id, base_service_id=forch.FogServiceID.DOCKER.value))

    return container

  def destroy_service_docker(self, service_id, *, prune=True):
    for c in self.docker_container_list():
      if c.name.startswith(service_id):
        c.stop()
    if prune:
      self.docker_container_prune()
    return service_id

  def destroy_all_services_docker(self):
    active_service_list = self.get_active_service_list()
    active_docker_service_id_list = [ active_s.get_service_id() for active_s in active_service_list
      if active_s.get_base_service_id() == "FVE001" ] # TODO avoid hardcoding
    if active_docker_service_id_list:
      logger.debug(f"Remove services {active_docker_service_id_list}")
      process_list = []
      for as_id in active_docker_service_id_list:
        p = multiprocessing.Process(target=self.destroy_service_docker, args=(as_id,), kwargs={"prune": False})
        p.start()
        process_list.append(p)
      for p in process_list:
        p.join()
      self.docker_container_prune()
    else:
      logger.debug("No Docker service to destroy")

### API Resources

class Test(Resource):
  def get(self):
    return {
      "message": f"This component ({Path(__file__).name}) is up!",
      "type": "FN_TEST_OK"
    }

class FogServices(Resource):
  # this GET replies with the active services, while available services (referred to as just "services") are discovered via SLP
  def get(self, s_id=""):
    as_id_list = [ s.get_id() for s in FNVI.get_instance().get_active_service_list() ]
    return {
      "message": f"Found {len(as_id_list)} active service(s)",
      "type": "FN_LS",
      "services": as_id_list
      }, 200

  def put(self, s_id):
    """Allocate service."""
    # TODO
    # request_json = flask.request.get_json(force=True)
    return {
      "message": f"Allocated service {s_id}",
      "type": "FN_ALLC_OK",
      # "name": container_name,
      # "ip": container_ip, # TODO change in IP visible from outside
      # "port_mappings": port_mappings
      }, 200

  def post(self, s_id):
    """Deploy service."""

    request_json = flask.request.get_json(force=True)

    assert "base" in request_json, f"Must specify a base service (FVExxx)"
    assert "FVE" in request_json["base"], f"Must specify valid base service (FVExxx)"
    base_id = request_json["base"]

    if base_id == forch.FogServiceID.DOCKER.value:
      assert "image" in request_json, f"Must specify image in {request_json}"
      image_name = request_json["image"]

      conf_dict = request_json["conf"]

      container = FNVI.get_instance().deploy_service_docker(s_id, image_name, **conf_dict)

      assert container is not None, f'Error deploying service {s_id}, check image name "{image_name}"'

      # refresh attrs dictionary
      container.reload()
      container_name = container.name # equivalent to container.attrs["Name"].strip("/")
      container_ip = container.attrs["NetworkSettings"]["IPAddress"]
      
      # port_mappings = [ f'{host_port_dict["HostIp"]}:{host_port_dict["HostPort"]}->{container_port}'
      #   for host_port_dict in container.attrs["NetworkSettings"]["Ports"][container_port]
      #   for container_port in container.attrs["NetworkSettings"]["Ports"]
      #   ]
      # equivalent to
      port_mappings = {}
      ports_dict = container.attrs["NetworkSettings"]["Ports"]
      for container_port in ports_dict:
        for host_port_dict in ports_dict[container_port]:
          # port_map = f'{host_port_dict["HostIp"]}:{host_port_dict["HostPort"]}->{container_port}'
          # port_mappings[host_port_dict["HostPort"]] = container_port
          port_mappings[container_port] = host_port_dict["HostPort"]
          # logger.debug(port_map)
      
      logger.debug(f"Deployed service {s_id} using image {image_name} on container {container_name} with address {container_ip} and ports {port_mappings}")

      return {
        "message": f"Deployed service {s_id} on {base_id} with image {image_name}",
        # "type": "FN_DEPL_OK",
        "name": container_name,
        "ip": container_ip,
        "port_mappings": port_mappings
        }, 201

    elif base_id == "FVExxx":
      # to be implemented if node supports different FVE other than Docker
      pass
    else:
      # TODO improve
      return {
        "message": f"Unknown base service {base_id}",
        # "type": "FN_DEPL_OK",
        # "name": container_name,
        # "ip": container_ip, # TODO change in IP visible from outside
        # "port_mappings": port_mappings
        }, 404

  def delete(self, s_id=""):
    if s_id:
      FNVI.get_instance().destroy_service(s_id)
      return {
        "message": f"Deleted services matching {s_id}",
        # "type": "FN_DEL_OK",
        }, 200
    else:
      FNVI.get_instance().destroy_all_services()
      return {
        "message": f"Deleted all services",
        # "type": "FN_DEL_OK",
        }, 200
    

if __name__ == '__main__':

  ### Command line argument parser

  import argparse

  default_address = "0.0.0.0"

  parser = argparse.ArgumentParser()
  parser.add_argument("-a", "--address", help="This component's IP address", nargs="?", default=default_address)
  parser.add_argument("-p", "--port", help="This component's TCP port", type=int, nargs="?", default=6001)
  parser.add_argument("-d", "--debug", help="Run in debug mode, default: false", action="store_true", default=False)
  args = parser.parse_args()

  if args.address == default_address:
    logger.warning(f"Running with default IP address {args.address}")

  ### instantiate components

  # FNVI.get_instance().set_ipv4("192.168.64.123")
  FNVI.get_instance().set_ipv4(args.address)
  FNVI.get_instance().load_service_list_from_json(str(Path(__file__).parent.joinpath("fnode_services.json").absolute()))
  FNVI.get_instance().register_service_list()
  FNVI.get_instance().find_active_services()

  ### REST API

  app = flask.Flask(__name__)
  api = Api(app)

  api.add_resource(Test, '/test')
  api.add_resource(FogServices, '/services', '/services/<s_id>')
  
  try:
    app.run(host=args.address, port=args.port, debug=args.debug)
  except KeyboardInterrupt:
    pass
  finally:
    logger.info("Cleanup after interruption")
    FNVI.del_instance()
