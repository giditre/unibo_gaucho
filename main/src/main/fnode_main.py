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
    if forch.is_orchestrator():
      ipv4 = IPv4Address("127.0.0.1")
    else:
      ipv4 = self.get_ipv4()
    
    assert ipv4 is not None, "Must set an IP address for this node first, using .set_ipv4(ipv4)"

    self.__service_list = forch.Service.create_services_from_json(json_file_name=json_file_name, ipv4=ipv4)

  def get_ipv4(self):
    return self.__ipv4

  def set_ipv4(self, ipv4):
    if isinstance(ipv4, str):
      ipv4 = IPv4Address(ipv4)
    assert isinstance(ipv4, IPv4Address), "Parameter ipv4 must be an IPv4Address object!"
    self.__ipv4 = ipv4

  def __get_docker_client(self):
    if self.__docker_client is None:
      self.__docker_client_init()
    return self.__docker_client

  def __docker_client_init(self):
    self.__docker_client = docker.from_env()
  
  def docker_client_test(self):
    return self.__get_docker_client().ping()
    
  def docker_image_is_cached(self, image_name):
    return len(self.__get_docker_client().images.list(name=image_name)) > 0

  def docker_image_pull(self, image_name, *, tag="latest"):
    if not self.docker_image_is_cached(image_name):
      logger.info(f"Need to pull image {image_name}")
      try:
        self.__get_docker_client().images.pull(image_name, tag=tag)
      except docker.errors.ImageNotFound:
        return None
    return self.__get_docker_client().images.get(image_name)


  def docker_container_run(self, image_name, **kwargs):
    img = self.docker_image_pull(image_name)
    if img is None:
      return None
    logger.info(f'Run container {kwargs["name"]}')
    return self.__get_docker_client().containers.run(image_name, **kwargs)

  def docker_container_prune(self):
    logger.debug('Prune containers')
    r = self.__get_docker_client().containers.prune()
    deleted_list = r["ContainersDeleted"]
    logger.info(f"Pruned {len(deleted_list)} containers")
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
    assert container_name not in [ c.name for c in self.__get_docker_client().containers.list() ], f"Name {container_name} already in use by container {self.__get_docker_client().containers.get(container_name)}"
    return container_name

  def list_containerized_services_docker(self):
    return list(set([ c.name.split("_")[0] for c in self.__get_docker_client().containers.list() ]))

  def deploy_service_docker(self, service_id, image_name):

    container_name = self.__generate_container_name(service_id, image_name)

    logger.debug(f"Deploy service {service_id} with container {container_name} using image {image_name}")

    container = self.docker_container_run(image_name, name=container_name, hostname=container_name, detach=True, stdin_open=True, tty=True, publish_all_ports=True, command=None, entrypoint=None)

    if container is None:
      return None

    return container

  def destroy_service_docker(self, service_id, *, prune=True):
    for c in self.__get_docker_client().containers.list():
      if c.name.startswith(service_id):
        c.stop()
    if prune:
      self.docker_container_prune()

  def destroy_all_services_docker(self):
    process_list = []
    for s_id in FNVI.get_instance().list_containerized_services_docker():
      p = multiprocessing.Process(target=self.destroy_service_docker, args=(s_id,), kwargs={"prune": False})
      p.start()
      process_list.append(p)
    for p in process_list:
      p.join()
    self.docker_container_prune()

### API Resources

class Test(Resource):
  def get(self):
    return {
      "message": f"This component ({Path(__file__).name}) is up!",
      "type": "FN_TEST_OK"
    }

class FogServices(Resource):
  # this GET replies with the services in the MEC sense (i.e., deployed containers); services in the XaaS sense are discovered via SLP
  def get(self, s_id=""):
    s_id_list = FNVI.get_instance().list_containerized_services_docker()
    return {
      "message": f"Found {len(s_id_list)} service(s)",
      "type": "FN_LS",
      "services": s_id_list
      }, 200

  def put(self, s_id):
    """Allocate service."""
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

    if base_id == "FVE001":
      assert "image" in request_json, f"Must specify image in {request_json}"
      image_name = request_json["image"]

      container = FNVI.get_instance().deploy_service_docker(s_id, image_name)

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
        "type": "FN_DEPL_OK",
        "name": container_name,
        # "ip": container_ip, # TODO change in IP visible from outside
        "port_mappings": port_mappings
        }, 201

  def delete(self, s_id=""):
    if s_id:
      FNVI.get_instance().destroy_service_docker(s_id)
      return {
        "message": f"Deleted services matching {s_id}",
        "type": "FN_DEL_OK",
        }, 200
    else:
      FNVI.get_instance().destroy_all_services_docker()
      return {
        "message": f"Deleted all deployed services",
        "type": "FN_DEL_OK",
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
