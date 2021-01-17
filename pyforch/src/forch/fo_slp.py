# RECALL:
# slp.SLP_LIFETIME_DEFAULT = 10800
# slp.SLP_LIFETIME_MAXIMUM = 65535

# This import allows to hint custom classes and to use | instead of Union[]
# TODO: remove it when Python 3.10 will be used
from __future__ import annotations
import logging
import os
from typing import Dict, List, Tuple
import warnings

# from logging.config import fileConfig
# from pathlib import Path
# fileConfig(str(Path(__file__).parent.joinpath("logging.conf")))
# logger = logging.getLogger("fuslp")
# logger.info("Load {} with {}".format(__name__, logger))

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

import shlex
import subprocess
import re
from enum import Enum
from socket import getservbyname
import time
from pathlib import Path

import slp

from . import raise_error
from .fo_service import Service

_SLP_ATTRIBUTES_SEPARATOR = ','

# SLP services known attributes
class _SLPAttributes(Enum):
  ID = "id"
  CATEGORY = "category"
  DESCRIPTION = "descr"

  # https://stackoverflow.com/questions/43634618/how-do-i-test-if-int-value-exists-in-python-enum-without-using-try-catch/43634746
  @classmethod
  def has_value(cls, value:object):
    return value in cls._value2member_map_ # pylint: disable=no-member

class SLPFactory:
  __common_slp_agent = None
  __common_agents_counter = 0

  @classmethod
  def create_UA(cls, new_handler:bool=False):
    """This method creates and returns a UserAgent object.

    Args:
        new_handler (bool, optional): specifies if a new SLP handler must be created for this agent. Defaults to False.

    Returns:
        SLPFactory.__UserAgent: the created UA.
    """
    if not bool(new_handler):
      slp_handler = cls.__get_common_handler()
      cls.__increment_agents_counter()
      return cls.__UserAgent(slp_handler)
    return cls.__UserAgent(None)

  @classmethod
  def create_SA(cls, new_handler:bool=False):
    """This method creates and returns a ServiceAgent object.

    Args:
        new_handler (bool, optional): specifies if a new SLP handler must be created for this agent. Defaults to False.

    Returns:
        SLPFactory.__ServiceAgent: the created SA.
    """
    if not bool(new_handler):
      slp_handler = cls.__get_common_handler()
      cls.__increment_agents_counter()
      return cls.__ServiceAgent(slp_handler)
    return cls.__ServiceAgent(None)

  @classmethod
  def create_DA(cls, new_handler:bool=False):
    """This method creates and returns a DirectoryAgent object.

    Args:
        new_handler (bool, optional): specifies if a new SLP handler must be created for this agent. Defaults to False.

    Returns:
        SLPFactory.__DirectoryAgent: the created DA.
    """
    if not bool(new_handler):
      slp_handler = cls.__get_common_handler()
      cls.__increment_agents_counter()
      return cls.__DirectoryAgent(slp_handler)
    return cls.__DirectoryAgent(None)

  # In Java this would be a protected method
  @classmethod
  def _get_common_agents_counter(cls):
    return cls.__common_agents_counter

  @classmethod
  def __increment_agents_counter(cls):
    cls.__common_agents_counter += 1

  # In Java this would be a protected method
  @classmethod
  def _decrement_agents_counter(cls):
    cls.__common_agents_counter -= 1
    if cls.__common_agents_counter == 0:
      cls.__destroy_common_slp_agent()

  @classmethod
  def __get_common_handler(cls) -> object:
    if cls.__common_slp_agent is None:
      assert cls._get_common_agents_counter() == 0, "If i'm here __agents_counter is supposed to be 0"
      cls.__common_slp_agent = cls.__SLPAgent()
    return cls.__common_slp_agent.get_handler()

  @classmethod
  def __destroy_common_slp_agent(cls):
    cls.__common_slp_agent = None # Set to None in order to destroy the agent instance

  class __SLPAgent:
    def __init__(self, slp_handler:object|None=None):
      """Generic SLP Agent constructor.

      Args:
          slp_handler (object|None, optional): if not None, the agent is initialized with this previously created handler. Defaults to None.
      """
      self.__new_handler = False
      self.__hslp = slp_handler
      if self.__hslp is None:
        self.__new_handler = True
        self.__hslp: object = slp.SLPOpen("en", False)
        logger.debug(self.__hslp)

    def __del__(self):
      if SLPFactory._get_common_agents_counter() == 0:
        slp.SLPClose(self.__hslp)
      else:
        if self.__new_handler:
          slp.SLPClose(self.__hslp)
        else:
          SLPFactory._decrement_agents_counter()

    def get_handler(self) -> object:
      """This method return the SLP handler of the agent.

      Returns:
          object: SLP agent handler (hslp).
      """
      return self.__hslp

  # Attenction: Only one slpd at a time is allowed, otherwise it is a mess!
  class __SLPActiveAgent(__SLPAgent):

    def __del__(self):
      super().__del__()
      self.__stop_daemon()

    @classmethod
    def __daemon_is_running(cls) -> bool:
      return bool(cls.__get_daemon_pid())

    @staticmethod
    def __get_daemon_pid() -> int|None:
      out = subprocess.run(shlex.split("pgrep slpd"), capture_output=True).stdout.decode('utf-8')
      if not out:
        return None # TODO: maybe it is better to raise an error
      assert out.count("\n") == 1, "Found more than one slpd PID!"
      return int(out)

    @classmethod
    def _start_daemon(cls, optns:str="") -> bool:
      assert isinstance(optns, str), "Parameter optns must be a string!"

      if cls.__daemon_is_running():
        logger.warning("Local slpd is already running.")
        return False
        #raise_error(self.__class__, "Daemon is already running!")

      cmd_str = "slpd"

      if optns != None and optns != "":
        cmd_str += " " + optns

      if not os.geteuid() == 0:
        cmd_str = "sudo " + cmd_str

      subprocess.run(shlex.split(cmd_str))

      # Maybe this while is useless because previously we called run() instead of Popen(), but since run() is considered as a black box, it is better to stay on the safe side.
      while not cls.__daemon_is_running():
        time.sleep(0.1)

      return True
    
    @classmethod
    def __stop_daemon(cls) -> bool:
      try:
        if not cls.__daemon_is_running():
          return False
      except ImportError:
        cmd_str = "pkill -15 slpd" # This has been done as hotfix for the next comment. Find a better alternative.
      else:
        cmd_str = "kill -15 {}".format(cls.__get_daemon_pid())

      if not os.geteuid() == 0:
        cmd_str = "sudo " + cmd_str

      try:
        subprocess.run(shlex.split(cmd_str)) # TODO: find a way to stop slpd in the destructor
      except ImportError:
        logger.warning("subprocess.run() cannot be called during destruction. slpd will remain active.")
        warnings.warn("subprocess.run() cannot be called during destruction. slpd will remain active.")

      return True
      
    # def kill_daemon(self):
    #   if not self.daemon_is_running():
    #     return False
    #   self.__daemon_process.kill()
    #   return True
      
  class __UserAgent(__SLPAgent):
    __discovery_list = []

    def find_all_services(self) -> List[Service]:
      """This method search and returns all SLP announced network services.

      Returns:
          List[Service]: found services list.
      """
      srvc_types_list = self.__find_srvc_types()
      srvc_types_list = list(set(srvc_types_list)) #if equals elements are returned keep only one of them

      found_srvs_list = []
      for srvc_type in srvc_types_list:
        found_srvs_list.extend(self.__find_service(srvc_type))
      # Now it should be checked if the list contain equal elements. If yes keep only one of them
      # Theoretically the previous comment is already solved in the return instruction by aggregate_nodes_of_equal_services()

      srvs_dict = {}
      for i, srvc_tuple in enumerate(found_srvs_list):
        srvs_dict.update({srvc_tuple[0]:self.__find_attr_list(srvc_tuple[0]), ("lifetime#" + str(i)):srvc_tuple[1]})

      srvs_list = []
      srvc = None
      for key in srvs_dict:
        if key.split("#")[0] != "lifetime":
          srvc = self.__srvurl_to_service(key) # in this case key = srvurl

          if srvs_dict[key] != "":
            tmp_srvc = self.__attrs_to_service(srvs_dict[key])
            if tmp_srvc is None:
              raise_error(self.__class__.__name__, "Unexpected __attrs_to_service result!")

            srvc.set_id(tmp_srvc.get_id())
            srvc.set_category(tmp_srvc.get_category())
            srvc.set_descr(tmp_srvc.get_descr())
          else:
            # TODO: raise error because attributes must be present?
            pass
        else:
          assert isinstance(srvc, Service), "Unexpected type of srvc: " + type(srvc)
          node_list = srvc.get_node_list()
          assert len(node_list) == 1 if node_list != None else False, "In theory here we have only one node associated to a service"
          node_list[0].set_lifetime(srvs_dict[key]) # in this case key = lifetime
          srvs_list.append(srvc)

      return Service.aggregate_nodes_of_equal_services(srvs_list)

    @staticmethod
    def __srvurl_to_service(srvurl:str) -> Service:
      parsed_data = slp.SLPParseSrvURL(srvurl)
      logger.debug("Parsed URL: {}".format(parsed_data))
      srvc_type, url, host_port, _, _ = parsed_data

      assert re.match("^service(:[a-zA-Z0-9.]+){2,2}$", srvc_type), "Service type is not custom. It must contain at least two ':'"
      _, name, protocol = srvc_type.split(":")

      if url.endswith("/"):
        url = url[:-1]
      try:
        host_ipv4, path = url.split("/", 1)
      except:
        host_ipv4 = url
        path = ""

      if host_port <= 0 or host_port > 0xffff:
        host_port = getservbyname(protocol)

      srvc = Service(name=name, protocol=protocol)
      srvc.add_node(ipv4=host_ipv4, port=host_port, path=path)
      # TODO: maybe check return value and, if Zabbix didn't found the node found by SLP, raise an exception?
      return srvc

    @staticmethod
    def __attrs_to_service(attrs_str:str) -> Service|None:
      if attrs_str == "":
        return None

      tmp_attrs_list = attrs_str.split(_SLP_ATTRIBUTES_SEPARATOR)

      attrs_list = []
      for attr in tmp_attrs_list:
        attrs_list.extend(attr.split("="))

      srvc = Service()

      for i in range(0, len(attrs_list), 2):
        if attrs_list[i] == _SLPAttributes.ID.value:
          srvc.set_id(attrs_list[i+1])
        elif attrs_list[i] == _SLPAttributes.CATEGORY.value:
          srvc.set_category(attrs_list[i+1])
        elif attrs_list[i] == _SLPAttributes.DESCRIPTION.value:
          srvc.set_descr(attrs_list[i+1])
        elif _SLPAttributes.has_value(attrs_list[i]):
          logger.warning("Known service attribute {} not used.".format(attrs_list[i]))
        else:
          raise_error(__class__.__name__, "Unexpected service attribute received!") # TODO: is a simple warning sufficient?

      if srvc.get_id() == "":
        return None

      return srvc
      
    # Expected inputs: {key1:value1, key2:value2, ...}, int, string
    # errcode and rqst_type are only for debug
    @staticmethod
    def __rqsts_callback_core(param_dict:Dict[str,str|int], errcode:int, rqst_type:str="") -> bool:
      rv = False
      if errcode == slp.SLP_OK:
        for key in param_dict:
          logger.debug("{}: {}".format(key, param_dict[key]))
          #print("{}: {}".format(key,param_dict[key]))
        rv = True
      elif errcode == slp.SLP_LAST_CALL:
        pass
      else:
        print("Error: " + str(errcode))
      return rv
    
    @staticmethod
    def __srvc_types_callback(h:object, srvc_type:str, errcode:int, cookie_data:object) -> bool:
      res = __class__.__rqsts_callback_core({"srvc_type":srvc_type}, errcode, "service types")
      if res == True:
        __class__.__discovery_list = srvc_type.split(",")
      return res

    @staticmethod
    def __service_callback(h:object, srvurl:str, lifetime:int, errcode:int, cookie_data:object) -> bool:
      res = __class__.__rqsts_callback_core({"url":srvurl, "timeout":lifetime}, errcode, "service")
      if res == True:
        __class__.__discovery_list.append((srvurl, lifetime))
      return res

    @staticmethod
    def __attr_callback(h:object, attrs:str, errcode:int, cookie_data:object) -> bool:
      res = __class__.__rqsts_callback_core({"attrs":attrs}, errcode, "attribute lists")
      if res == True:
        __class__.__discovery_list.append(attrs)
      return res

    def __find_srvc_types(self) -> List[str]:
      self.__class__.__discovery_list = []
      try:
        slp.SLPFindSrvTypes(self.get_handler(), "*", "", self.__srvc_types_callback, None)
      except RuntimeError as e:
        raise_error(self.__class__.__name__, "Error discovering the service types: " + str(e))
      return self.__class__.__discovery_list
      
    def __find_service(self, service_type:str) -> List[Tuple[str, int]]:
      self.__class__.__discovery_list = []
      try:
        slp.SLPFindSrvs(self.get_handler(), service_type, None, None, self.__service_callback, None)
      except RuntimeError as e:
        raise_error(self.__class__.__name__, "Error discovering the service: " + str(e))
      return self.__class__.__discovery_list

    def __find_attr_list(self, srvurl:str) -> str:
      self.__class__.__discovery_list = []
      try:
        slp.SLPFindAttrs(self.get_handler(), srvurl, None, None, self.__attr_callback, None)
      except RuntimeError as e:
        raise_error(self.__class__.__name__, "Error discovering the service attributes: " + str(e))
      if not self.__class__.__discovery_list:
        return ""

      res = list(set(self.__class__.__discovery_list))[0]
      assert len(set(self.__class__.__discovery_list)) == 1 and isinstance(res, str), "Unexpected attribute response"
      return res

  class __ServiceAgent(__SLPActiveAgent):
    def __init__(self, slp_handler:object=None):
      super()._start_daemon("-c {}".format(str(Path(__file__).parent.joinpath("slp_SA.conf")))) # in this case "super()" can be replaced by "self"
      super().__init__(slp_handler)
      self.__reg_srvc: List[Service] = [] # If useful, make __reg_srvc getter.

    def __del__(self):
      for srvc in self.__reg_srvc:
        self.deregister_service(srvc)
      super().__del__()

    def register_service(self, service:Service):
      """This method register a given input service in order to be announced using SLP. Each registered service is automatically deregistered during SA destruction.

      Args:
          service (Service): service to be registered.
      """
      srvurl_list, attrs, lifetime_list = self.__service_to_slp_service(service)
      for i, srvurl in enumerate(srvurl_list):
        self.__register_service(srvurl, attrs, lifetime_list[i])
      self.__reg_srvc.append(service)

    def deregister_service(self, service:Service):
      """This method deregister a given input service.

      Args:
          service (Service): service to be deregistered.
      """
      srvurl_list = self.__service_to_slp_service(service)[0]
      for srvurl in srvurl_list:
        self.__deregister_service(srvurl)
      if service in self.__reg_srvc:
        self.__reg_srvc.remove(service)
      else:
        logger.warning("Deregistered a service that either was not registered by this SA, or had already been deregistered.")

    @staticmethod
    def __service_to_slp_service(service:Service) -> Tuple[List[str], str, List[int]]:
      assert isinstance(service, Service), "Parameter service must be a Service() object!"
      srvc_type = "service:" + service.get_name() + ":" + service.get_protocol()

      srvurl_list = []
      lifetime_list = []
      for node in service.get_node_list():
        path = node.get_path()
        if not path.startswith("/"):
          path = "/" + path
        srvurl_list.append(srvc_type + "://" + str(node.get_ip()) + ":" + str(node.get_port()) + path)
        lifetime_list.append(node.get_lifetime())

      attrs = _SLPAttributes.ID.value + "=" + service.get_id() + _SLP_ATTRIBUTES_SEPARATOR + _SLPAttributes.CATEGORY.value + "=" + service.get_category().name + _SLP_ATTRIBUTES_SEPARATOR + _SLPAttributes.DESCRIPTION.value + "=" + service.get_descr()

      return (srvurl_list, attrs, lifetime_list)

    @staticmethod
    def __reg_callback(h:object, errcode:int, data:object) -> None:
      if errcode != slp.SLP_OK:
        logger.warning("Error de/registering service: " + str(errcode))
      return None

    def __register_service(self, srvurl:str, attrs:str="", lifetime:int=slp.SLP_LIFETIME_DEFAULT):
      # TODO this is just a temporary fix
      attempts = 1
      while attempts <= 3:
        try:
          slp.SLPReg(self.get_handler(), srvurl, lifetime, None, attrs, True, self.__reg_callback, None)
        except RuntimeError as e:
          # TODO use logger instead of print everywhere
          logger.error(f"Error in attempt {attempts} at registering new service: {e}") # TODO undestand why it often raises SLP_NETWORK_INIT_FAILED error
          attempts += 1
          time.sleep(3)
        else:
          logger.debug(f"Service registered on attempt {attempts}")
          break

    def __deregister_service(self, srvurl:str):
      try:
        slp.SLPDereg(self.get_handler(), srvurl, self.__reg_callback, None)
      except RuntimeError as e:
        print("Error deregistering service: " + str(e))

  class __DirectoryAgent(__SLPActiveAgent):
    def __init__(self, slp_handler:object=None):
      slp.SLPSetProperty("net.slp.isDA", "true") # Maybe useless, but it sets correctly the global environment
      super()._start_daemon("-c {}".format(str(Path(__file__).parent.joinpath("slp_DA.conf")))) # in this case "super()" can be replaced by "self"
      super().__init__(slp_handler)
