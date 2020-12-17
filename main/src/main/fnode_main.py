import logging
from logging.config import fileConfig
from pathlib import Path
fileConfig(str(Path(__file__).parent.joinpath("logging.ini")))
logger = logging.getLogger(__name__)
logger.info(f"Load {__name__} with {logger}")

from ipaddress import IPv4Address, IPv4Network
from time import time
import multiprocessing
import sys
import configparser
import socket

import flask
from flask_restful import Resource, Api

import docker

import forch
logger.debug("Running as orchestrator? {}".format(forch.is_orchestrator()))


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

  def find_active_services(self, *, service_category_list=["APP", "SDP"]):
    # find pre-existing services
    # cycle over known base services
    for base_service_id in [forch.FogServiceID.DOCKER.value]:
      if base_service_id == forch.FogServiceID.DOCKER.value:
        # Docker-specific
        for cont_name in [ c.name for c in self.docker_container_list() if any(c.name.startswith(service_category) for service_category in service_category_list) ]:
          cont_s_id = cont_name.split("-")[0]
          logger.debug(f"Found active service {cont_s_id} base {forch.FogServiceID.DOCKER.value} on container {cont_name}")
          self.update_active_service_list(forch.ActiveService(service_id=cont_s_id, base_service_id=forch.FogServiceID.DOCKER.value, instance_name=cont_name))
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
    # check if service is of category IaaS, meaning it must be deallocated
    if service_id.startswith(forch.ServiceCategory.IAAS.value):
      # service is of category IaaS
      # TODO deallocate
      pass
    else:
      # service is NOT of category IaaS -- need to discover base_service_id
      # get relevant instance of ActiveService
      # TODO move this search to a function, handling non-existent service ?
      active_service_list = [ s for s in self.get_active_service_list() if s.get_service_id() == service_id ]
      active_base_service_id_list = [ s.get_base_service_id() for s in active_service_list ]
      base_to_instance_list_dict = { base_service_id: [ active_s.get_instance_name() for active_s in active_service_list
        if active_s.get_instance_name()
        ]
        for base_service_id in active_base_service_id_list
      }
      for base_service_id, instance_name_list in base_to_instance_list_dict.items():
        if service_id == base_service_id:
          # TODO deallocate
          pass
        else:
          # destroy
          if base_service_id == forch.FogServiceID.DOCKER.value:
            return self.destroy_container_list_docker(instance_name_list) # TODO make this multiprocessing (the method to destroy a list of containers already exists, but)
          elif base_service_id == "FVExxx":
            pass
          else:
            pass

      # for active_s in active_service_list:
      #   # check if service_id == base_service_id, meaning service is allocated, else service is deployed
      #   base_service_id = active_s.get_base_service_id()
      #   if active_s.get_service_id() == base_service_id:
      #     # TODO deallocate
      #     pass
      #   else:
      #     # destroy
      #     if base_service_id == forch.FogServiceID.DOCKER.value:
      #       # instance_list = [ s.get_instance_name() for s in active_service_list if s.get_instance_name()]
      #       return self.destroy_container_docker(active_s.get_instance_name()) # TODO make this multiprocessing (the method to destroy a list of containers already exists, but)
      #     elif base_service_id == "FVExxx":
      #       pass
      #     else:
      #       pass

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
      assert IPv4Network(subnet), "Must provide a valid IPv4 subnet in CIDR notation!"
      assert IPv4Network(dhcp_range), "Must provide a valid IPv4 subnet in CIDR notation!"

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

  def __generate_container_name(self, service_id, *, image_name=None):
    # TODO avoid hardcoding separator
    container_name = "-".join([
      service_id,
      # image_name.replace("/", "-").replace(":", "-"),
      str(int(time()*1000)) # or '{0:%Y%m%d-%H%M%S-%f}'.format(datetime.now())
      ])
    # check length (limit imposed by hostname field)
    assert len(container_name) < 64, f"Name {container_name} is longer than 63 chars"
    # check there is no other container with this name
    assert container_name not in [ c.name for c in self.docker_container_list() ], f"Name {container_name} already in use by container {self.__get_docker_client().containers.get(container_name)}"
    return container_name

  def list_containerized_services_docker(self, *, service_category_list=["APP", "SDP"]):
    # TODO avoid hardcoding separator
    return list(set([ c.name.split("-")[0] for c in self.docker_container_list()
      if any(c.name.startswith(service_category) for service_category in service_category_list) ]))

  def deploy_container_docker(self, service_id, image_name, **kwargs):

    container_name = self.__generate_container_name(service_id)

    logger.debug(f"Deploy service {service_id} with container {container_name} using image {image_name}")

    container = self.docker_container_run(image_name, name=container_name, hostname=container_name, **kwargs)

    if container is None:
      return None

    # just before returning, update active service list
    self.update_active_service_list(forch.ActiveService(service_id=service_id, base_service_id=forch.FogServiceID.DOCKER.value, instance_name=container_name))

    return container

  def destroy_container_docker(self, container_name, *, prune=True):
    for c in self.docker_container_list():
      if c.name == container_name:
        c.stop()
        break
    if prune:
      self.docker_container_prune()      
      self.docker_network_prune()
    return container_name

  def destroy_container_list_docker(self, container_name_list, *, prune=True):
    logger.debug(f"Remove containers {container_name_list}")
    process_list = []
    for container_name in container_name_list:
      p = multiprocessing.Process(target=self.destroy_container_docker, args=(container_name,), kwargs={"prune": False})
      p.start()
      process_list.append(p)
    for p in process_list:
      p.join()
    if prune:
      self.docker_container_prune()      
      self.docker_network_prune()
    return container_name_list

  def destroy_all_containers_docker(self):
    active_service_list = self.get_active_service_list()
    active_docker_container_name_list = [ active_s.get_instance_name() for active_s in active_service_list
      if active_s.get_base_service_id() == forch.FogServiceID.DOCKER.value ]
    if active_docker_container_name_list:
      self.destroy_container_list_docker(active_docker_container_name_list)
    else:
      logger.debug("No Docker containers to destroy")
    return active_docker_container_name_list

### API Resources

class Test(Resource):
  def get(self):
    return {
      "message": f"Component {Path(__file__).name} on {socket.gethostname()} is up!",
      # "type": "FN_TEST_OK"
    }

class FogServices(Resource):
  # this GET replies with the active services, while available services (referred to as just "services") are discovered via SLP
  def get(self, s_id=""):
    as_list = [ {
      "service_id": s.get_service_id(),
      "base_service_id": s.get_base_service_id(),
      "node_id": s.get_node_id(),
      "instance_name": s.get_instance_name(),
      "instance_ip": s.get_instance_ip()
    } for s in FNVI.get_instance().get_active_service_list() ]
    return {
      "message": f"Found {len(as_list)} active service(s)",
      # "type": "FN_LS",
      "services": as_list
      }, 200

  def put(self, s_id):
    """Allocate service."""
    # TODO
    # request_json = flask.request.get_json(force=True)
    return {
      "message": f"Allocated service {s_id}",
      # "type": "FN_ALLC_OK",
      # "name": container_name,
      # "ip": container_ip, # TODO change in IP visible from outside
      # "port_mappings": port_mappings
      }, 200

  def post(self, s_id):
    """Deploy service."""

    request_json = flask.request.get_json(force=True)

    assert forch.InstanceConfiguration.BASE.value in request_json, f"Must specify a base service"
    assert forch.ServiceCategory.IAAS.value in request_json[forch.InstanceConfiguration.BASE.value], f"Must specify valid base service ({forch.ServiceCategory.IAAS.value}xxx)"
    base_id = request_json[forch.InstanceConfiguration.BASE.value]

    if base_id == forch.FogServiceID.DOCKER.value:
      assert forch.InstanceConfiguration.IMAGE.value in request_json, f"Must specify image in {request_json}"
      image_name = request_json[forch.InstanceConfiguration.IMAGE.value]

      if "instance_conf" in request_json: # TODO avoid hardcoding string
        instance_conf_dict = request_json["instance_conf"] 

        # preliminary configuration
        # if a network configuration is requested, check that the network exists
        if forch.DockerContainerConfiguration[forch.InstanceConfiguration.ATTACH_TO_NETWORK.value].value in instance_conf_dict:
          network_name = instance_conf_dict[forch.DockerContainerConfiguration[forch.InstanceConfiguration.ATTACH_TO_NETWORK.value].value]
          if FNVI.get_instance().docker_network_exists(network_name) == False:
            logger.debug(f"Network {network_name} does not exist")
            # create it, based on network configuration info in the JSON
            # these configs are assumed to be compatible with the employed Docker method
            network_conf_dict = request_json["network_conf"] # TODO avoid hardcoding string
            FNVI.get_instance().docker_network_create_with_bridge(network_name, **network_conf_dict)
            # TODO check network was correctly created
      else:
        instance_conf_dict = {
          forch.DockerContainerConfiguration[forch.InstanceConfiguration.DETACH.value].value: True,
          forch.DockerContainerConfiguration[forch.InstanceConfiguration.KEEP_STDIN_OPEN.value].value: True,
          forch.DockerContainerConfiguration[forch.InstanceConfiguration.ALLOCATE_TERMINAL.value].value: True,
          forch.DockerContainerConfiguration[forch.InstanceConfiguration.FORWARD_ALL_PORTS.value].value: True
        }

      container = FNVI.get_instance().deploy_container_docker(s_id, image_name, **instance_conf_dict)

      assert container is not None, f'Error deploying service {s_id}, check image name "{image_name}"'
      assert container != b'', f'Error deploying service {s_id}, check run parameters'

      # refresh attrs dictionary
      container.reload()
      container_name = container.name # equivalent to container.attrs["Name"].strip("/")
      container_ip = container.attrs["NetworkSettings"]["IPAddress"]
      if not container_ip:
        container_ip = container.attrs["NetworkSettings"]["Networks"][container.attrs["HostConfig"]["NetworkMode"]]["IPAddress"]
      
      
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


# def cleanup():
#   try:
#     logger.info("Cleanup")
#   finally:
#     FNVI.del_instance()

### argument parser

# import argparse

# default_address = "0.0.0.0"
# default_port = forch.get_fog_node_main_port()

# parser = argparse.ArgumentParser()
# parser.add_argument("-a", "--address", help=f"This component's IP address, default: {default_address}",
#   nargs="?", default=default_address)
# parser.add_argument("-p", "--port", help=f"This component's TCP port, default: {default_port}", type=int,
#   nargs="?", default=default_port)
# parser.add_argument("-d", "--debug", help="Run in debug mode", action="store_true", default=False)
# args = parser.parse_args()

# if args.address == default_address:
#   logger.warning(f"Running with default IP address {args.address}")

local_config = forch.get_local_config(Path(__file__).parent.joinpath("fnode.ini").absolute())
logger.debug(f"Config: {dict(local_config.items())}")

### instantiate components

FNVI.get_instance().set_ipv4(local_config["address"])
FNVI.get_instance().load_service_list_from_json(str(Path(__file__).parent.joinpath(local_config["services_json"]).absolute()))
FNVI.get_instance().register_service_list()
FNVI.get_instance().find_active_services() # this might raise a RuntimeError
# TODO add configuration flag for this

### REST API

app = flask.Flask(__name__)
api = Api(app)

api.add_resource(Test, '/test')
api.add_resource(FogServices, '/services', '/services/<s_id>')

if __name__ == "__main__":

  try:
    app.run(host=local_config.get("address"),
      port=local_config.getint("port"),
      debug=local_config.getboolean("debug"))
  except KeyboardInterrupt:
    pass
  finally:
    logger.info("Cleanup after interruption")
    FNVI.del_instance()
