import logging
from logging.config import fileConfig
from pathlib import Path
fileConfig(str(Path(__file__).parent.joinpath("logging.ini")))
logger = logging.getLogger(__name__)
logger.info(f"Load {__name__} with {logger}")

from ipaddress import IPv4Address
import time
from datetime import datetime

from flask import Flask, request
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
    
  def docker_image_is_cached(self, image_uri):
    return len(self.__get_docker_client().images.list(name=image_uri)) > 0

  def docker_image_pull(self, image_uri, *, tag="latest"):
    if not self.docker_image_is_cached(image_uri):
      logger.info(f"Need to pull image {image_uri}")
      self.__get_docker_client().images.pull(image_uri, tag=tag)

  def docker_container_run(self, image_uri, **kwargs):
    self.docker_image_pull(image_uri)
    logger.info(f'Run container {kwargs["name"]}')
    return self.__get_docker_client().containers.run(image_uri, **kwargs)

  def deploy_service(self, service_id, image_uri):
    container_name = "_".join([
      service_id,
      image_uri.replace("/", "-").replace(":", "-"),
      '{0:%Y%m%d-%H%M%S-%f}'.format(datetime.now())
      ])
    container_hostname = container_name if len(container_name) <= 63 else container_name[:63]

    logger.debug(f"Deploy service {service_id} in container {container_name} with image {image_uri}")

    container = self.docker_container_run(image_uri, name=container_name, hostname=container_hostname, detach=True, stdin_open=True, tty=True, publish_all_ports=True, restart_policy={"Name": "on-failure", "MaximumRetryCount": 3}, command=None, entrypoint=None)

    return container

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

  ### instantiate components

  FNVI.get_instance().set_ipv4("192.168.64.123")
  FNVI.get_instance().load_service_list_from_json(str(Path(__file__).parent.joinpath("service_example.json").absolute()))

  ### REST API

  app = Flask(__name__)
  api = Api(app)

  api.add_resource(Test, '/test')
  # api.add_resource(FogServices, '/services', '/services/<s_id>')
  
  try:
    app.run(host=args.address, port=args.port, debug=args.debug)
  except KeyboardInterrupt:
    pass
  finally:
    logger.info("Cleanup after interruption")
    FNVI.del_instance()