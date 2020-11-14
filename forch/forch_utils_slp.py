# RECALL:
# slp.SLP_LIFETIME_DEFAULT = 10800
# slp.SLP_LIFETIME_MAXIMUM = 65535

import sys
import shlex
import subprocess
import re
from enum import IntEnum, Enum
from abc import ABCMeta, abstractmethod
import warnings

import slp

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
      if self.__hslp == None:
        self.__hslp = self.__hslp = slp.SLPOpen("en", False) #TODO M: valutare se usare OpenSLP in maniera sincrona o asincrona. Con False è sincrona
        print(self.__hslp)

    def __del__(self):
      slp.SLPClose(self.__hslp)

    def get_handler(self):
      return self.__hslp

    # This method is intended as abstract
    @abstractmethod
    def get_type(self):
      return

  # TODO M: decidere se poter avere più demoni (max uno per ogni agente) o averne soltanto uno e basta. N.B.: credo che SLP non lo preveda. Cercare di capirlo
  # This class is used like a sort of interface
  class _SLPActiveAgent(_SLPAgent):
    __daemon_process = None

    def __init__(self,slp_handler=None):
      self.start_daemon() #TODO M: controllare valore di ritorno?
      super().__init__(slp_handler)

    def __del__(self):
      super().__del__()
      self.stop_daemon()

    def daemon_is_running(self):
      if self.__daemon_process != None:
        if self.__daemon_process.poll() == None:
          return True      
      return False
    
    def start_daemon(self,optns_str=""):#,parameters):
      if self.daemon_is_running():
        raise_error(self.__class__, "Daemon is already running!")
        #return False

      cmd_str = "sudo slpd"

      if optns_str != "":
        cmd_str = " " + optns_str

      self.__daemon_process = subprocess.Popen(shlex.split(cmd_str))

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
    # Warning! static vars
    # TODO M: valutare se servono 3 liste o ne basta una
    __discovery_list = None

    def get_type(self):
      return SLPAgentType.UA
      
    # Expected inputs: string, {key1:value1, key2:value2, ...}, string
    # prints, count and rqst_type are only for debug
    @staticmethod
    def __rqsts_callback_core(param_dict,errcode,rqst_type=""):
      global count
      rv = False
      if errcode == slp.SLP_OK:
        for key in param_dict:
          print("{}: {}".format(key,param_dict[key]), end=", ")
        count += 1 # pylint: disable=undefined-variable
        rv = True
      elif errcode == slp.SLP_LAST_CALL:
        if count == 0:
          print(rqst_type + ": Nothing found")
        else:
          print("Found " + str(count) + " " + rqst_type)
      else:
        print("Error: " + str(errcode))
      return rv
    
    @staticmethod
    def __srvc_types_callback(h, srvc_type, errcode, cookie_data):
      res = SLPController._UA.__rqsts_callback_core({"srvc_type":srvc_type},str(errcode),"service types")
      if res == True:
        SLPController._UA.__discovery_list.append(srvc_type)
      return res

    @staticmethod
    def __service_callback(h, srvurl, lifetime, errcode, cookie_data):
      res = SLPController._UA.__rqsts_callback_core({"url":srvurl, "timeout":lifetime},str(errcode),"service")
      if res == True:
        SLPController._UA.__discovery_list.append((srvurl,lifetime))
      return res

    @staticmethod
    def __attr_callback(h, attrs, errcode, cookie_data):
      res = SLPController._UA.__rqsts_callback_core({"attrs":attrs},str(errcode),"attribute lists")
      if res == True:
        SLPController._UA.__discovery_list.append(attrs)
      return res

    def find_srvc_types(self):
      count = 0 # pylint: disable=unused-variable
      self.__discovery_list = []
      try:
        slp.SLPFindSrvTypes(self.get_handler(), "*", "", self.__srvc_types_callback, None)
      except RuntimeError as e:
        print("Error discovering the service types: " + str(e))
        return None
      return self.__discovery_list
      
    def find_service(self, service_type):
      count = 0 # pylint: disable=unused-variable
      self.__discovery_list = []
      try:
        slp.SLPFindSrvs(self.get_handler(), service_type, None, None, self.__service_callback, None)
      except RuntimeError as e:
        print("Error discovering the service: " + str(e))
        return None
      return self.__discovery_list

    def find_attr_list(self, srvurl):
      count = 0 # pylint: disable=unused-variable
      self.__discovery_list = []
      try:
        slp.SLPFindAttrs(self.get_handler(), srvurl, None, None, self.__attr_callback, None)
      except RuntimeError as e:
        print("Error discovering the service attributes: " + str(e))
        return None
      return self.__discovery_list
  
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
      raise_error(__class__,'Passed an invalid agent parameter')

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
      srvurl_list.append(srvc_type + "://" + node.get_ip() + ":" + node.get_port() + path)
      lifetime_list.append(node.get_lifetime())

    attrs = SLPAttributes.ID + service.get_id() + SLPController._ATTRIBUTES_SEPARATOR + SLPAttributes.CATEGORY + service.get_category() + SLPController._ATTRIBUTES_SEPARATOR + SLPAttributes.DESCRIPTION + service.get_descr()

    return (srvurl_list, attrs, lifetime_list)

  @staticmethod
  def __srvurl_to_service(srvurl):
    srvc_type, url, host_port = slp.SLPParseSrvURL(srvurl)
    assert re.match("^service(:[a-zA-Z0-9.]+){2,2}$", srvc_type), "Service type is not custom. It must contain at least two ':'"
    host_ipv4, path = url.split("/", 1)
    srvc = Service(name=srvc_type.split(":")[1], protocol=srvc_type.split(":")[2])
    srvc.add_node(ipv4=host_ipv4, port=host_port, path=path)
    # TODO: maybe check return value se Zabbix non trova il nodo che ha trovato SLP e in caso exception?
    return srvc

  @staticmethod
  def __attrs_to_service(attrs_str):
    tmp_attrs_list = attrs_str.split(SLPController._ATTRIBUTES_SEPARATOR)

    attrs_list = []
    for attr in tmp_attrs_list:
      attrs_list.extend(attr.slip("="))

    srvc = Service()

    for i in range(0, len(attrs_list), 2):
      if attrs_list[i] == SLPAttributes.ID:
        srvc.set_id(attrs_list[i+1])
      elif attrs_list[i] == SLPAttributes.CATEGORY:
        srvc.set_category(attrs_list[i+1])
      elif attrs_list[i] == SLPAttributes.DESCRIPTION:
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
      srvc = None
      if key.split("#")[0] != "lifetime":
        srvc = self.__srvurl_to_service(key) # in this case key = srvurl
        tmp_srvc = self.__attrs_to_service(srvs_dict[key])
        
        srvc.set_id(tmp_srvc.get_id())
        srvc.set_category(tmp_srvc.get_category())
        srvc.set_descr(tmp_srvc.get_descr())
      else:
        assert len(srvc.get_node_list()) == 1, "In theory here we have only one node associated to a service"
        srvc.get_node_list()[0].set_lifetime(srvs_dict[key]) # in this case key = lifetime
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
