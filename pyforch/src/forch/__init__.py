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

from .fo_service import Service, MetricType, MeasurementRetrievalMode
from .fo_servicecache import ServiceCache
from .fo_slp import SLPFactory
from .fo_zabbix import ZabbixAPI, ZabbixAdapter, ZabbixNode, ZabbixNodeFields

# __all__ = ()

class ActiveService(Service):

  def __init__(self, *, service_id, node_ip=None, base_service_id=None):
    super().__init__(id=service_id)

    self.__service_id = self.get_id()
    self.__node_id = self.add_node(ipv4=node_ip) if node_ip is not None else None
    self.__base_service_id = base_service_id if base_service_id is not None else self.__service_id
  
  def __eq__(self, obj):
    if isinstance(obj, self.__class__):
      return ( self.get_service_id() == obj.get_service_id()
        and self.get_node_id() == obj.get_node_id()
        and self.get_base_service_id() == obj.get_base_service_id()
        )
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

  # def add_node(self, *args, **kwargs):
  #   super().add_node(*args, **kwargs)