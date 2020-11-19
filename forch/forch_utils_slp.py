# RECALL:
# slp.SLP_LIFETIME_DEFAULT = 10800
# slp.SLP_LIFETIME_MAXIMUM = 65535

import logging
from logging.config import fileConfig
fileConfig("logging_config.ini")
logger = logging.getLogger("fuslp")
logger.info("Load {} with {}".format(__name__, logger))

import sys
import shlex
import subprocess
import re
from enum import IntEnum, Enum
from abc import ABCMeta, abstractmethod
import warnings
from socket import getservbyname
import psutil
import time

import slp

from forch import IS_ORCHESTRATOR
from forch.forch_utils_service import Service
from forch.forch_tools import raise_error

class SLPAgentType(IntEnum):
  UA = 1
  SA = 2
  DA = 3

# SLP services known attributes
class SLPAttributes(Enum):
  ID = "id"
  CATEGORY = "category"
  DESCRIPTION = "descr"

  # https://stackoverflow.com/questions/43634618/how-do-i-test-if-int-value-exists-in-python-enum-without-using-try-catch/43634746
  @classmethod
  def has_value(cls, value):
    return value in cls._value2member_map_ # pylint: disable=no-member

# This class exposes methods dedicated to the different types of agents.
# If a method is used in a wrong agent context, Python will return errors
# saying that one or more methods are not defined
# More or less SLPController is a _SLPAgent wrapper
class SLPController:
  #TODO M: se la storia degli abstract da troppi problemi toglierla. Proviamo a tenerla per il momento. Override dentro _SLPActiveAgent nuovamente abstract necessario?
  class _SLPAgent(metaclass=ABCMeta):
    def __init__(self, slp_handler=None):
      self.__hslp = slp_handler
      if self.__hslp is None:
        self.__hslp = slp.SLPOpen("en", False)
        logger.debug(self.__hslp)

    def __del__(self):
      slp.SLPClose(self.__hslp)

    def get_handler(self):
      return self.__hslp

    # This method is intended as abstract
    @abstractmethod
    def get_type(self):
      return

  # Attenction: Only one slpd at a time is allowed, otherwise it is a mess!
  class _SLPActiveAgent(_SLPAgent):
    __daemon_process = None

    def __init__(self,slp_handler=None):
      self.start_daemon() #TODO M: controllare valore di ritorno?
      super().__init__(slp_handler)

    def __del__(self):
      super().__del__()
      self.stop_daemon()
      #self.kill_daemon()
      #self.__daemon_process.wait()

    def daemon_is_running(self):
      if self.__daemon_process != None:
        if self.__daemon_process.poll() is None:
          return True      
      return False
    
    def start_daemon(self,optns_str=""):#,parameters):
      if self.daemon_is_running():
        warnings.warn("Local slpd is already running.")
        return False
        #raise_error(self.__class__, "Daemon is already running!")
      #subprocess.Popen(shlex.split("sudo pkill -9 -f slpd"))
      # TODO M: fare check se ci sono processi slpd esterni? Nel caso terminarli o solo errore?

      cmd_str = "sudo slpd -d" # without -d, slpd survive also if the program terminates

      if optns_str != "":
        cmd_str += " " + optns_str

      self.__daemon_process = subprocess.Popen(shlex.split(cmd_str))
      while not psutil.Process(self.__daemon_process.pid).children():
        time.sleep(0.01)

      # print(shlex.split(cmd_str))
      # padre = subprocess.Popen(shlex.split(cmd_str))
      # while not psutil.Process(padre.pid).children():
      #   pass
      # pid_figlio = psutil.Process(padre.pid).threads()
      # pid_figlio = psutil.Process(padre.pid).children()[0].pid
      # padre.wait()
      # self.__daemon_process = pid_figlio

      return True
      
    def stop_daemon(self):
      if not self.daemon_is_running():
        return False
      self.__daemon_process.terminate() # TODO M: controllare se è davvero terminato ed eventualmente fare .kill()? Per adesso ci fidiamo.
      return True
      
    def kill_daemon(self):
      if not self.daemon_is_running():
        return False
      self.__daemon_process.kill()
      return True
      
  class _UA(_SLPAgent):
    __discovery_list = None

    def get_type(self):
      return SLPAgentType.UA
      
    # Expected inputs: string, {key1:value1, key2:value2, ...}, string
    # prints, count and rqst_type are only for debug
    @staticmethod
    def __rqsts_callback_core(param_dict,errcode,rqst_type=""):
      rv = False
      if errcode == slp.SLP_OK:
        for key in param_dict:
          logger.debug("{}: {}".format(key,param_dict[key]))
          #print("{}: {}".format(key,param_dict[key]))
        rv = True
      elif errcode == slp.SLP_LAST_CALL:
        pass
      else:
        print("Error: " + str(errcode))
      return rv
    
    @staticmethod
    def __srvc_types_callback(h, srvc_type, errcode, cookie_data):
      res = SLPController._UA.__rqsts_callback_core({"srvc_type":srvc_type}, errcode, "service types")
      if res == True:
        SLPController._UA.__discovery_list = srvc_type.split(",")
      return res

    @staticmethod
    def __service_callback(h, srvurl, lifetime, errcode, cookie_data):
      res = SLPController._UA.__rqsts_callback_core({"url":srvurl, "timeout":lifetime}, errcode, "service")
      if res == True:
        SLPController._UA.__discovery_list.append((srvurl,lifetime))
      return res

    @staticmethod
    def __attr_callback(h, attrs, errcode, cookie_data):
      res = SLPController._UA.__rqsts_callback_core({"attrs":attrs}, errcode, "attribute lists")
      if res == True:
        SLPController._UA.__discovery_list.append(attrs)
      return res

    def find_srvc_types(self):
      self.__class__.__discovery_list = []
      try:
        slp.SLPFindSrvTypes(self.get_handler(), "*", "", self.__srvc_types_callback, None)
      except RuntimeError as e:
        print("Error discovering the service types: " + str(e))
        return None
      return self.__discovery_list
      
    def find_service(self, service_type):
      self.__class__.__discovery_list = []
      try:
        slp.SLPFindSrvs(self.get_handler(), service_type, None, None, self.__service_callback, None)
      except RuntimeError as e:
        print("Error discovering the service: " + str(e))
        return None
      return self.__discovery_list

    def find_attr_list(self, srvurl):
      self.__class__.__discovery_list = []
      try:
        slp.SLPFindAttrs(self.get_handler(), srvurl, None, None, self.__attr_callback, None)
      except RuntimeError as e:
        print("Error discovering the service attributes: " + str(e))
        return None
      if not self.__discovery_list:
        return ""

      res = list(set(self.__discovery_list))[0]
      assert len(set(self.__discovery_list)) == 1 and isinstance(res, str), "Unexpected attribute response"
      return res
  
  class _SA(_SLPActiveAgent):
    def get_type(self):
      return SLPAgentType.SA

    @staticmethod
    def __reg_callback(h, errcode, data):
      if errcode != slp.SLP_OK:
        print("Error de/registering service: " + str(errcode))
      return None

    def register_service(self, srvurl, attrs="", lifetime=slp.SLP_LIFETIME_DEFAULT):
      try:
        slp.SLPReg(self.get_handler(), srvurl, lifetime, None, attrs, True, self.__reg_callback, None)
      except RuntimeError as e:
        print("Error registering new service: " + str(e))

    def deregister_service(self, srvurl):
      try:
        slp.SLPDereg(self.get_handler(), srvurl, self.__reg_callback, None)
      except RuntimeError as e:
        print("Error deregistering service: " + str(e))

  class _DA(_SLPActiveAgent):
    def __init__(self, slp_handler=None):
      slp.SLPSetProperty("net.slp.isDA", "true")
      super().__init__(slp_handler)

    def get_type(self):
      return SLPAgentType.DA

  # Begin of SLPController class code

  _ATTRIBUTES_SEPARATOR = ','

  def __init__(self,agent,slp_handler = None):
    if agent == SLPAgentType.UA:
      #TODO M: in teoria queste non dovrebbero essere necessarie perchè il protocollo dovrebbe trovare il DA locale e parlare solo con lui in unicast. Verificare
      #slp.SLPSetProperty("net.slp.interfaces", "127.0.0.1")
      #slp.SLPSetProperty("net.slp.DAAddresses", "127.0.0.1")
      self.__agent = self._UA(slp_handler)
    elif agent == SLPAgentType.SA:
      self.__agent = self._SA(slp_handler)
    elif agent == SLPAgentType.DA:
      self.__agent = self._DA(slp_handler)
    else:
      raise_error(self.__class__,'Passed an invalid agent parameter')

  def get_handler(self):
    return self.__agent.get_handler()

  def get_agent_type(self):
    return self.__agent.get_type()

  @staticmethod
  def __service_to_slp_service(service):
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

    attrs = SLPAttributes.ID.value + "=" + service.get_id() + SLPController._ATTRIBUTES_SEPARATOR + SLPAttributes.CATEGORY.value + "=" + service.get_category() + SLPController._ATTRIBUTES_SEPARATOR + SLPAttributes.DESCRIPTION.value + "=" + service.get_descr()

    return (srvurl_list, attrs, lifetime_list)

  @staticmethod
  def __srvurl_to_service(srvurl):
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
    # TODO: maybe check return value se Zabbix non trova il nodo che ha trovato SLP e in caso exception?
    return srvc

  @staticmethod
  def __attrs_to_service(attrs_str):
    if attrs_str == "":
      return None

    tmp_attrs_list = attrs_str.split(SLPController._ATTRIBUTES_SEPARATOR)

    attrs_list = []
    for attr in tmp_attrs_list:
      attrs_list.extend(attr.split("="))

    srvc = Service()

    for i in range(0, len(attrs_list), 2):
      if attrs_list[i] == SLPAttributes.ID.value:
        srvc.set_id(attrs_list[i+1])
      elif attrs_list[i] == SLPAttributes.CATEGORY.value:
        srvc.set_category(attrs_list[i+1])
      elif attrs_list[i] == SLPAttributes.DESCRIPTION.value:
        srvc.set_descr(attrs_list[i+1])
      elif SLPAttributes.has_value(attrs_list[i]):
        warnings.warn("Known service attribute {} not used.".format(attrs_list[i]))
      else:
        raise_error(__class__, "Unexpected service attribute received!") # TODO M: forse mettere un semplice warning?

    return srvc
      
  def find_all_services(self):
    srvc_types_list = self.__agent.find_srvc_types()
    srvc_types_list = list(set(srvc_types_list)) #if equals elements are returned keep only one of them

    found_srvs_list = []
    for srvc_type in srvc_types_list:
      found_srvs_list.extend(self.__agent.find_service(srvc_type))
    # TODO M: verificare se è possibile che la lista contenga elementi uguali. Nel caso toglierli
    # NOTE: Il TODO precedente dovrebbe essere automaticamente risolto nell'istruzione di return

    srvs_dict = {}
    for i, srvc_tuple in enumerate(found_srvs_list):
      srvs_dict.update({srvc_tuple[0]:self.__agent.find_attr_list(srvc_tuple[0]), ("lifetime#" + str(i)):srvc_tuple[1]})

    srvs_list = []
    for key in srvs_dict:
      if key.split("#")[0] != "lifetime":
        srvc = self.__srvurl_to_service(key) # in this case key = srvurl

        if srvs_dict[key] != "":
          tmp_srvc = self.__attrs_to_service(srvs_dict[key])

          srvc.set_id(tmp_srvc.get_id())
          srvc.set_category(tmp_srvc.get_category())
          srvc.set_descr(tmp_srvc.get_descr())
        else:
          #TODO M: mettere errore perchè gli attributi ci devono essere?
          pass
      else:
        #TODO M: da decommentare il prima possibile! assert len(srvc.get_node_list()) == 1, "In theory here we have only one node associated to a service"
        srvc.get_node_list()[0].set_lifetime(srvs_dict[key]) # in this case key = lifetime
        # if IS_ORCHESTRATOR:
        #   assert len(srvc.get_node_list()) == 1, "In theory here we have only one node associated to a service"
        #   srvc.get_node_list()[0].set_lifetime(srvs_dict[key]) # in this case key = lifetime
        # else:
        #   assert len(srvc.get_node_list()) == 2, "I thought that here there were only two nodes..."
        #   srvc.get_node_list()[1].set_lifetime(srvs_dict[key]) # in this case key = lifetime
        #   assert srvc.get_node_list()[0].fully_equals_to(srvc.get_node_list()[1]), "Something is wrong. Announced node must be equal to the discovered one"
        #   srvc.get_node_list().pop(-1)
        srvs_list.append(srvc)

    return Service.aggregate_nodes_of_equal_services(srvs_list)

  def register_service(self, service):
    srvurl_list, attrs, lifetime_list = self.__service_to_slp_service(service)
    for i, srvurl in enumerate(srvurl_list):
      self.__agent.register_service(srvurl, attrs, lifetime_list[i])

  def deregister_service(self, service):
    srvurl_list = self.__service_to_slp_service(service)[0]
    for srvurl in srvurl_list:
      self.__agent.deregister_service(srvurl)
