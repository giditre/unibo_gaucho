# This import allows to hint custom classes and to use | instead of Union[]
# TODO: remove it when Python 3.10 will be used
from __future__ import annotations
import logging
from typing import List

# from logging.config import fileConfig
# from pathlib import Path
# fileConfig(str(Path(__file__).parent.joinpath("logging.conf")))
# logger = logging.getLogger("fuservice")
# logger.info("Load {} with {}".format(__name__, logger))

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

from ipaddress import IPv4Address
from socket import getservbyname
from enum import Enum, IntEnum
import json
from pathlib import Path

from . import is_orchestrator
from .fo_zabbix import ZabbixAdapter, ZabbixNodeFields, MeasurementFields


class ServiceCategory(Enum):
  IAAS = "FVE"    # Fog Virtualization Engine
  PAAS = "SDP"    # Software Development Platform
  SAAS = "APP"    # APPlication
  FAAS = "LAF"    # Lightweight Atomic Function
  NONE = "None"


class MetricType(Enum):
  CPU = "CPU utilization"
  RAM = "Memory utilization"


class MeasurementRetrievalMode(IntEnum):
  SERVICE = 1
  NODE = 2
  METRIC = 3


class Service:
  __orchestrator: bool=False # default value will be never used in theory, but it is necessary to avoid pylint no-member error

  def __init__(self, *, name:str="", protocol:str="", node_list:List[Service.__ServiceNode]|None=None, id:str="", category:ServiceCategory|None=None, description:str=""):
    if node_list is None:
      node_list = []
    assert all( isinstance(node, self.__ServiceNode) for node in node_list ), "Parameter node_list must be a list of ServiceNode!"

    if category is not None:
      assert isinstance(category, ServiceCategory), "Parameter category must be of type ServiceCategory!"
    else:
      category = ServiceCategory.NONE

    self.__class__.__orchestrator = is_orchestrator()

    self.__name: str = name
    self.__protocol: str = protocol
    self.__node_list: List[Service.__ServiceNode] = node_list
    self.__id: str = id
    self.__category: ServiceCategory = category
    self.__description: str = description

  def __repr__(self):
    return str(self.__dict__)
 
  def __eq__(self, obj):
    if isinstance(obj, self.__class__):
      return self.get_id() == obj.get_id()
    return False

  def get_name(self):
    return self.__name
  def set_name(self, name:str):
    self.__name = name

  def get_protocol(self):
    return self.__protocol
  def set_protocol(self, protocol:str):
    self.__protocol = protocol

  def get_node_list(self):
    return self.__node_list
  # def __set_node_list(self, node_list):
  #   self.__node_list = node_list

  def get_id(self):
    return self.__id
  def set_id(self, id:str):
    self.__id = id

  def get_category(self):
    return self.__category
  def set_category(self, category:ServiceCategory):
    self.__category = category

  def get_descr(self):
    return self.__description
  def set_descr(self, description:str):
    self.__description = description

  # def to_json(self):
  #   # return json.dumps(self.__dict__, default=lambda x: str(x))
  #   return self.__dict__

  # This is the convergence point between Zabbix and SLP
  def add_node(self, *, ipv4:IPv4Address, port:int=0, path:str="", lifetime:int=0xffff) -> str|None:
    """
    This is the convergence point between Zabbix and SLP.
    Adds a node to the service. Requires at least the IP address of the node.
    Retrieves information on the node from Zabbix if this is run on the Zabbix Server.
    Returns the ID of the created node, or None if node not found in Zabbix.
    """
    if isinstance(ipv4, str):
      ipv4 = IPv4Address(ipv4)
    assert isinstance(ipv4, IPv4Address), "Parameter ipv4 must be an IPv4Address objects!"

    # merge with zabbix only if is_orchestrator
    if self.__class__.__orchestrator:
      node = ZabbixAdapter.get_instance().get_node_by_ip(ipv4)
      logger.debug("Retrieved ZabbixNode {}".format(node))
      node_dict = node.to_dict()
      node_dict[ZabbixNodeFields.AVAILABLE.value] = node_dict[ZabbixNodeFields.AVAILABLE.value] == "1"

      if node_dict[ZabbixNodeFields.AVAILABLE.value]:
        node = self.__ServiceNode(id=node_dict[ZabbixNodeFields.ID.value], ipv4=ipv4, name=node_dict[ZabbixNodeFields.NAME.value], available=node_dict[ZabbixNodeFields.AVAILABLE.value], port=port, path=path, lifetime=lifetime)

        for elem in MetricType:
          node.add_metric(m_id=ZabbixAdapter.get_instance().get_item_id_by_node_and_item_name(node_dict[ZabbixNodeFields.ID.value], elem.value), m_type=elem)

        self.get_node_list().append(node)

        return node.get_id()

      else:
        logger.info("Node {} not added in service {} because, according to Zabbix, unavailable.".format(str(ipv4), self.__repr__()))
        return None
      
      # # create metrics list for this node
      # m_list = [ self.__ServiceNode._Metric(id=ZabbixAdapter.get_instance().get_item_id_by_node_and_item_name(node_dict[MeasurementFields.NODE_ID], elem.value), m_type=elem) for elem in MetricType ]

      # # instatiate new ServiceNode and append it to node list
      # self.get_node_list().append(self.__ServiceNode(id=node_dict[MeasurementFields.NODE_ID], ipv4=ipv4, name=node_dict["name"], available=node_dict["is_available"], port=port, path=path, lifetime=lifetime, metrics_list=m_list))
    else:
      # instatiate new ServiceNode and append it to node list
      node_id = str(ipv4)
      self.get_node_list().append(self.__ServiceNode(id=node_id, ipv4=ipv4, port=port, path=path, lifetime=lifetime))
      return node_id

  def get_node_by_id(self, node_id:str) -> Service.__ServiceNode|None:
    # assert ...
    try:
      return next(sn for sn in self.get_node_list() if sn.get_id() == node_id)
    except StopIteration:
      return None

  # Useful links:
  # https://stackoverflow.com/questions/9835762/how-do-i-find-the-duplicates-in-a-list-and-create-another-list-with-them
  # https://stackoverflow.com/questions/9542738/python-find-in-list
  @classmethod
  def aggregate_nodes_of_equal_services(cls, service_list:List[Service]) -> List[Service]: # TODO: find a more concise name
    assert isinstance(service_list, list), "Parameter service_list must be a list!"
    ret_list = []
    for srvc in service_list:
      assert isinstance(srvc, Service), "Parameter service_list must contains Service objects!"
      if srvc not in ret_list:
        ret_list.append(srvc)
      else:
        new_node_list = ret_list[ret_list.index(srvc)].get_node_list()
        new_node_list.extend(srvc.get_node_list())
        new_node_list = list(set(new_node_list))
        ret_list[ret_list.index(srvc)] = cls(name=srvc.get_name(), protocol=srvc.get_protocol(), node_list=new_node_list, id=srvc.get_id(), category=srvc.get_category(), description=srvc.get_descr())
    return ret_list

  def get_node_by_metric(self, m_type:MetricType=MetricType.CPU, check:str="min") -> Service.__ServiceNode|None:
    assert isinstance(m_type, MetricType), "Parameter m_type must be a MetricType!"

    # check is there are nodes offering this service
    if not self.__node_list:
      return None
    
    # get list of a specified metric from the node list
    metric_list = []
    for node in self.__node_list:
      metric = node.get_metric_by_type(m_type)
      if metric != None:
        metric_list.append(metric)
        
    # check is there are metrics associated to this node
    if not metric_list:
      return None
    
    # sorting metrics by value (https://docs.python.org/3/howto/sorting.html)
    if check == "min":
      # res_metric = sorted(metric_list, key=lambda metric: metric.get_value())[0]
      res_metric = min(metric_list, key=lambda metric: metric.get_value())
    elif check == "max":
      # res_metric = sorted(metric_list, key=lambda metric: metric.get_value())[-1]
      res_metric = max(metric_list, key=lambda metric: metric.get_value())
    else:
      return None
      
    # find the node that owns the result metric and return it
    for node in self.__node_list:
      # in questo if ci fa comodo l'override di __eq__ fatto nella classe Metric
      if res_metric == node.get_metric_by_type(m_type):
        return node
        
  def refresh_measurements(self, mode:MeasurementRetrievalMode=MeasurementRetrievalMode.SERVICE) -> None:
    assert self.__class__.__orchestrator, "This method cannot be called since this node in not the orchestrator!"
    assert isinstance(mode, MeasurementRetrievalMode), "Parameter mode must be a MeasurementRetrievalMode!"
    # check retrieval mode
    if mode == MeasurementRetrievalMode.SERVICE:
      # retrieve all measurements (of the defined metrics) of all nodes associated to this Service
      # get list of known nodes (it will be used multiple times)
      node_list = self.get_node_list()
      # retrieve all measurements for all nodes for all defined metric types
      # this returns a dictionary formatted as {'30254': {'node_id': '10313', 'metric_id': '30254', 'metric_name': 'CPU utilization', 'timestamp': '0', 'value': '0', 'unit': '%'}}
      measurements = ZabbixAdapter.get_instance().get_measurements_by_node_list([node.get_id() for node in node_list], item_name_list=[item.value for item in MetricType])
      # populate the data structure
      for node in node_list:
        for metric in node.get_metrics_list():
          m_id = metric.get_id()
          assert m_id in measurements, "Measurement of metric {} is not in provided measurements!".format(m_id)
          metric.set_timestamp(measurements[m_id][MeasurementFields.TIMESTAMP.value])
          metric.set_value(measurements[m_id][MeasurementFields.VALUE.value])
          if metric.get_unit() == "":
            metric.set_unit(measurements[m_id][MeasurementFields.UNIT.value])
    elif mode == MeasurementRetrievalMode.NODE:
      # refresh the value of all metrics of a node
      for node in self.get_node_list(): 
        measurements = ZabbixAdapter.get_instance().get_measurements_by_item_id_list([m.get_id() for m in node.get_metrics_list()])
        # populate the data structure
        for metric in node.get_metrics_list():
          m_id = metric.get_id()
          assert m_id in measurements, "Measurement of metric {} is not in provided measurements!".format(m_id)
          metric.set_timestamp(measurements[m_id][MeasurementFields.TIMESTAMP.value])
          metric.set_value(measurements[m_id][MeasurementFields.VALUE.value])
          if metric.get_unit() == "":
            metric.set_unit(measurements[m_id][MeasurementFields.UNIT.value])
    elif mode == MeasurementRetrievalMode.METRIC:
      # refresh the value of a single metric
      for node in self.get_node_list():
        for metric in node.get_metrics_list():
          measurements = ZabbixAdapter.get_instance().get_measurements_by_item_id(metric.get_id())
          m_id = metric.get_id()
          assert m_id in measurements, "Measurement of metric {} is not in provided measurements!".format(m_id)
          metric.set_timestamp(measurements[m_id][MeasurementFields.TIMESTAMP.value])
          metric.set_value(measurements[m_id][MeasurementFields.VALUE.value])
          if metric.get_unit() == "":
            metric.set_unit(measurements[m_id][MeasurementFields.UNIT.value])
    else:
      # should never happen
      pass
  
  # @classmethod
  # def __create_service_node_by_id(cls, node_id):
  #   return cls.__ServiceNode(id=node_id)

  # def create_and_add_node_by_id(self, node_id):
  #   self.get_node_list().append(self.__ServiceNode(id=node_id))

  # @classmethod
  # def create_service_by_id(cls, *, service_id, node_id_list=None):
  #   node_list = [ cls.__create_service_node_by_id(node_id=sn_id) for sn_id in node_id_list ]
  #   return cls(id=service_id, node_list=node_list)

  # @classmethod
  # def create_service_by_id(cls, service_id):
  #   return cls(id=service_id)

  @classmethod
  def create_services_from_json(cls, *, json_file_name:str|Path, ipv4:IPv4Address) -> List[Service]:
    if isinstance(ipv4, str):
      ipv4 = IPv4Address(ipv4)
    assert isinstance(ipv4, IPv4Address), "Parameter ipv4 must be an IPv4Address object!"
    assert isinstance(json_file_name, (str, Path)), "Parameter json_file_name must be a string!"
    assert Path(json_file_name).is_file(), "{} is not a file or it does not exist.".format(json_file_name)

    service_list = []

    with open(json_file_name, 'r') as f:
      jsonDict = json.load(f)

    for service_category in jsonDict:
      for service_id in jsonDict[service_category]:
        name = jsonDict[service_category][service_id]['name']
        protocol = jsonDict[service_category][service_id]['protocol']
        descr = jsonDict[service_category][service_id]['descr']
        try:
          port = int(jsonDict[service_category][service_id]['port'])
          if port <= 0 or port > 0xffff:
            port = None
        except:
          port = None

        if port == None:
          port = getservbyname(protocol)

        service_list.append(cls(name=name, protocol=protocol, id=service_id, category=ServiceCategory[service_category], description=descr, node_list=[cls.__ServiceNode(id=str(ipv4), ipv4=ipv4, path=jsonDict[service_category][service_id]['path'], lifetime=int(jsonDict[service_category][service_id]['lifetime']), port=port)]))

    return service_list


  class __ServiceNode:
    # 0xffff = slp.SLP_LIFETIME_MAXIMUM
    def __init__(self, *, id:str, ipv4:IPv4Address, name:str="", available:bool=False, port:int=0, path:str="", lifetime:int=0xffff, metrics_list:List[Service.__ServiceNode.__Metric]|None=None):
      if metrics_list is None:
        metrics_list = []
      for metric in metrics_list:
        assert isinstance(metric, self.__Metric), "Parameter metrics_list must be a list of Metric objects!"
      if isinstance(ipv4, str):
        ipv4 = IPv4Address(ipv4)
      assert isinstance(ipv4, IPv4Address), "Parameter ipv4 must be an IPv4Address objects!"
      
      self.__id: str = id
      self.__ip: IPv4Address = ipv4
      self.__name: str = name
      self.__available: bool = available
      self.__port: int = port
      self.__path: str = path
      self.__lifetime: int = lifetime
      self.__metrics_list: List[Service.__ServiceNode.__Metric] = metrics_list

    def __repr__(self):
      # return "{}(id={},name={},ip={},metrics={})".format(self.__class__.__name__, self.get_id(), self.get_name(), self.get_ip(), self.get_metrics_list())
      return str(self.__dict__)

    def __eq__(self, obj):
      if isinstance(obj, self.__class__):
        return self.get_id() == obj.get_id()
      return False

    # def to_dict(self):
    #   # TODO G
    #   pass

    # def to_json(self):
    #   # return json.dumps(self.__dict__, default=lambda o: str(o))
    #   return self.to_dict()

    # def to_pickle(self):
    #     return pickle.dumps(vars(self))

    # @classmethod
    # def from_pickle(cls, p):
    #   logger.debug(f"Create object {cls.__name__} from pickle {p}")
    #   o = cls(port=None, id=None)
    #   vars(o).update(pickle.loads(p))
    #   return o

    # def fully_equals_to(self, node):
    #   if not self.__eq__(node):
    #     return False

    #   check_list = [self.get_name()==node.get_name(), self.get_available()==node.get_available(), self.get_ip()==node.get_ip(), self.get_port()==node.get_port(), self.get_path()==node.get_path(), self.get_lifetime()==node.get_lifetime(), self.get_metrics_list()==node.get_metrics_list()]

    #   return all(check_list)
      
    def get_id(self):
 	    return self.__id 
    def set_id(self, id:str):
      self.__id = id

    def get_name(self):
      return self.__name    
    def set_name(self, name:str):
      self.__name = name

    def get_available(self):
      return self.__available    
    def set_available(self, available:bool):
      self.__available = available

    def get_ip(self):
      return self.__ip
    def set_ip(self, ipv4:IPv4Address):
      if isinstance(ipv4, str):
        ipv4 = IPv4Address(ipv4)
      assert isinstance(ipv4, IPv4Address), "Parameter ipv4 must me an IPv4Address!"
      self.__ip = ipv4

    def get_port(self):
      return self.__port
    def set_port(self, port:int):
      self.__port = port

    def get_path(self):
      return self.__path
    def set_path(self, path:str):
      self.__path = path

    def get_lifetime(self):
      return self.__lifetime
    def set_lifetime(self, lifetime:int):
      self.__lifetime = lifetime

    def get_metrics_list(self):
      return self.__metrics_list

    def add_metric(self, m_id:str, m_type:MetricType) -> None:
      assert isinstance(m_type, MetricType), "Parameter m_type must be a MetricType!"
      self.get_metrics_list().append(self.__Metric(m_id=m_id, m_type=m_type))
    
    # This method supposes that, for each MetricType, there is only a single MetricType entry in metrics_list
    def get_metric_by_type(self, m_type:MetricType) -> Service.__ServiceNode.__Metric|None:
      assert isinstance(m_type, MetricType), "Parameter m_type must be a MetricType!"
      #return next((metric for metric in self.__metric_list if metric.get_name() == m_type), None) # not used because readability    
      for metric in self.get_metrics_list():
        if metric.get_type() == m_type:
          return metric
      return None
      
    # def refresh_measurements(self): # TODO G: keep this method or not?
    #   # method to refresh the value of all metrics of a node
    #   measurements = ZabbixAdapter.get_instance().get_measurements_by_item_id([m.get_id() for m in self.get_metrics_list()])da dentro una sottoclasse?
    #   # populate the data structure
    #   for metric in node.get_metrics_list():
    #     m_id = metric.get_id()
    #     if m_id in measurements:
    #       metric.set_timestamp(measurements[m_id][MeasurementFields.TIMESTAMP])
    #       metric.set_value(measurements[m_id][MeasurementFields.VALUE])
    #       metric.set_unit(measurements[m_id][MeasurementFields.UNIT]) # TODO G: set the unit each time is useless (?)
    #     else:
    #       # TODO G: how can i handle the case in which a node have a metric that is not in the measurements? Is it possible to handle?
    #       pass


    class __Metric:
      def __init__(self, m_id:str="", m_type:MetricType=MetricType.CPU, timestamp:str="", value:str="", unit:str=""):
        self.__id: str = m_id
        self.__type: MetricType = m_type
        self.__timestamp: str = timestamp
        self.__value: str = value
        self.__unit: str = unit

      def __repr__(self):
        # return "{}(id={},type={},timestamp={},value={},unit={})".format(self.__class__.__name__, self.get_id(), self.get_type(), self.get_timestamp(), self.get_value(), self.get_unit())
        # return pickle.dumps(self).decode("utf-8")
        return str(self.__dict__)

      def __eq__(self, obj):
        if isinstance(obj, self.__class__):
          return self.get_id() == obj.get_id()
        return False
      
      def get_id(self):
        return self.__id
      def set_id(self, id:str):
        self.__id = id

      def get_type(self):
        return self.__type
      def set_type(self, m_type:MetricType):
        self.__type = m_type
        
      def get_timestamp(self):
        return self.__timestamp
      def set_timestamp(self, timestamp:str):
        self.__timestamp = timestamp
        
      def get_value(self):
        return self.__value
      def set_value(self, value:str):
        self.__value = value
      
      def get_unit(self):
        return self.__unit
      def set_unit(self, unit:str):
        self.__unit = unit

      # def to_dict(self):
      #   return {
      #     "id": self.get_id(),
      #     "type": self.get_type(),
      #     "timestamp": self.get_timestamp(),
      #     "value": self.get_value(),
      #     "unit": self.get_unit()
      #   }

      # def to_json(self):
      #   return json.dumps(self.to_dict())

      # @classmethod
      # def from_json(cls, m_json):
      #   m_dict = json.loads(m_json)
      #   assert m_dict["type"] in MetricType, ""
      #   return cls(m_id=m_dict["id"], m_type=MetricType[m_dict["type"]], timestamp=m_dict["timestamp"], value=m_dict["value"], unit=m_dict["unit"])

      # def to_pickle(self):
      #   return pickle.dumps(vars(self))

      # @classmethod
      # def from_pickle(cls, p):
      #   logger.debug(f"Create object {cls.__name__} from pickle {p}")
      #   o = cls()
      #   vars(o).update(pickle.loads(p))
      #   return o    
        
      # def refresh_measurements(self): # TODO G: keep this method or not?
      #   # method to refresh the value of a single metric
      #   measurements = ZabbixAdapter.get_instance().get_measurements_by_item_id(self.get_id())
      #   # populate the data structure
      #   m_id = self.get_id()
      #   if m_id in measurements:
      #     metric.set_timestamp(measurements[m_id][MeasurementFields.TIMESTAMP])
      #     metric.set_value(measurements[m_id][MeasurementFields.VALUE])
      #     metric.set_unit(measurements[m_id][MeasurementFields.UNIT]) # TODO G: inutile settare ogni volta le unità (?)
      #   else:
      #       # TODO G: how can i handle the case in which a node have a metric that is not in the measurements? Is it possible to handle?
      #     pass
