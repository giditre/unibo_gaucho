# Inside this module is used "sudo". Please start it with sudo permissions.
# In fo_slp there are various pylint suppressions
# Every test in *_SLP.py files in tests directory must be executed alone
# TODO M: fare classi dedicate alle eccezioni
# TODO M: vedere se mettere tutti gli enum in un unico file da importare in giro
# TODO M: rimettere thumbnail in service_example_json
# TODO M: vedere se servono davvero tutti i parametri dei vari costruttori, soprattuto per le classi in fo_service.py
# TODO M: prendere interrupt tastiera per killare slpd

# TODO G: attenzione che il campo value delle Metric è una stringa e quindi il sorting dei nodi basati su quel value potrebbe non dare il risultato desiderato

_IS_ORCHESTRATOR = False

def is_orchestrator():
  global _IS_ORCHESTRATOR
  return _IS_ORCHESTRATOR

def set_orchestrator():
  global _IS_ORCHESTRATOR
  _IS_ORCHESTRATOR = True

def get_lst(item):
  if item is None:
    return item
  return [item] if not isinstance(item, list) else item

def raise_error(class_name, msg=""):
  try:
    raise NameError(class_name)
  except NameError:
    print(msg)
    raise

from .fo_service import Service, MetricType, MeasurementRetrievalMode, ServiceCategory
from .fo_servicecache import ServiceCache
from .fo_slp import SLPFactory
from .fo_zabbix import ZabbixAPI, ZabbixAdapter, ZabbixNode, ZabbixNodeFields

# __all__ = ()

from enum import Enum


class FogServiceID(Enum):
  # APPs
  APACHE_WEB_SERVER = "APP001"
  STRESS = "APP002"
  TRANSCODER = "APP003"
  UNIBO_MEC_TEST = "APP004"
  # SDPs
  PYTHON = "SDP001"
  # FVEs
  DOCKER = "FVE001"


_FOG_NODE_MAIN_PORT = 6001

def get_fog_node_main_port():
  return _FOG_NODE_MAIN_PORT


class InstanceConfiguration(Enum):
  # general
  BASE = "base"
  IMAGE = "image"
  # specific
  ALLOCATE_TERMINAL = "allocate_terminal"
  ATTACH_TO_NETWORK = "network"
  COMMAND = "command"
  DETACH = "detach"
  DNS_OPTION = "dns_option"
  DNS_SEARCH = "dns_search"
  DNS_SERVER = "dns_server"
  ENTRYPOINT = "entrypoint"
  ENVIRONMENT_VARIABLE = "env_var"
  FORWARD_ALL_PORTS = "forward_all_ports"
  KEEP_STDIN_OPEN = "keep_stdin_open"
  SET_IPv4_ADDRESS = "ipv4"


DockerContainerConfiguration = Enum("DockerContainerConfiguration", {
  InstanceConfiguration.ALLOCATE_TERMINAL.value: "tty",
  InstanceConfiguration.ATTACH_TO_NETWORK.value: "network",
  InstanceConfiguration.COMMAND.value: "command",
  InstanceConfiguration.DETACH.value: "detach",
  InstanceConfiguration.DNS_OPTION.value: "dns_opt",
  InstanceConfiguration.DNS_SEARCH.value: "dns_search",
  InstanceConfiguration.DNS_SERVER.value: "dns",
  InstanceConfiguration.ENTRYPOINT.value: "entrypoint",
  InstanceConfiguration.ENVIRONMENT_VARIABLE.value: "env",
  InstanceConfiguration.FORWARD_ALL_PORTS.value: "publish_all_ports",
  InstanceConfiguration.KEEP_STDIN_OPEN.value: "stdin_open",
  InstanceConfiguration.SET_IPv4_ADDRESS.value: "ip"
})


class NetworkConfiguration(Enum):
  NAME = "network_name"
  BRIDGE_NAME = "bridge_name"
  IPv4_SUBNET = "ipv4_subnet"
  IPv4_RANGE = "ipv4_range"
  IPv4_GATEWAY = "ipv4_gateway"


DockerNetworkConfiguration = Enum("DockerNetworkConfiguration", {
  NetworkConfiguration.NAME.value: "network_name",
  NetworkConfiguration.BRIDGE_NAME.value: "bridge_name",
  NetworkConfiguration.IPv4_SUBNET.value: "subnet",
  NetworkConfiguration.IPv4_RANGE.value: "dhcp_range",
  NetworkConfiguration.IPv4_GATEWAY.value: "bridge_address"
})


class User():

  def __init__(self, name, *, id=None, role=None):
    self.__name = name
    self.__id = id
    self.__role = role

  def get_name(self):
    return self.__name
  def set_name(self, name) :
    self.__name = name

  def get_id(self):
    return self.__id
  def set_id(self, id) :
    self.__id = id

  def get_role(self):
    return self.__role
  def set_role(self, role) :
    self.__role = role


class Project():
  
  def __init__(self, name, *, id=None, user_list=None, instance_configuration_dict=None, network_configuration_dict=None):
    self.__name = name
    self.__id = id
    self.__user_list = user_list
    # dicts of configurations specific to this project, e.g., a network with a given IP address space on which all services deployed for this project must be
    self.__instance_configuration_dict = instance_configuration_dict 
    self.__network_configuration_dict = network_configuration_dict

  def get_name(self):
    return self.__name
  def set_name(self, name) :
    self.__name = name

  def get_id(self):
    return self.__id
  def set_id(self, id) :
    self.__id = id

  def get_user_list(self):
    return self.__user_list
  def set_user_list(self, user_list) :
    self.__user_list = user_list

  def get_instance_configuration_dict(self):
    return self.__instance_configuration_dict
  def set_instance_configuration_dict(self, instance_configuration_dict) :
    self.__instance_configuration_dict = instance_configuration_dict

  def get_network_configuration_dict(self):
    return self.__network_configuration_dict
  def set_network_configuration_dict(self, network_configuration_dict) :
    self.__network_configuration_dict = network_configuration_dict


class ActiveService(Service):

  def __init__(self, *, service_id, node_ip=None, base_service_id=None, instance_name=None, instance_ip=None, user=None, project=None):
    super().__init__(id=service_id)

    self.__service_id = self.get_id()
    self.__node_id = super().add_node(ipv4=node_ip) if node_ip is not None else None
    self.__base_service_id = base_service_id if base_service_id is not None else self.__service_id

    self.__instance_name = instance_name
    self.__instance_ip = instance_ip

    if user is not None:
      assert isinstance(user, User), ""
    self.__user = user

    if project is not None:
      assert isinstance(project, Project), ""
    self.__project = project
  
  def __eq__(self, obj):
    if isinstance(obj, self.__class__):
      return self.__dict__ == obj.__dict__
    return False

  def get_service_id(self):
    return self.__service_id
  def set_service_id(self, service_id) :
    self.__service_id = service_id

  def get_node_id(self):
    return self.__node_id
  def set_node_id(self, node_id) :
    self.__node_id = node_id

  def get_base_service_id(self):
    return self.__base_service_id
  def set_base_service_id(self, base_service_id) :
    self.__base_service_id = base_service_id

  def get_instance_name(self):
	  return self.__instance_name
  def set_instance_name(self, instance_name) :
	  self.__instance_name = instance_name

  def get_instance_ip(self):
	  return self.__instance_ip
  def set_instance_ip(self, instance_ip) :
	  self.__instance_ip = instance_ip

  def get_user(self):
	  return self.__user
  def set_user(self, user) :
	  self.__user = user

  def get_project(self):
    return self.__project
  def set_project(self, project) :
    self.__project = project

  def add_node(self, *args, ipv4, **kwargs):
    self.set_node_id(super().add_node(*args, ipv4=ipv4, **kwargs))