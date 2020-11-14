#TODO M: ricompilare OpenSLP per correggere alcuni bug: https://github.com/openslp-org/openslp
#TODO M: Se serve: mettere controllo dei parametri di input nei vari metodi (soprattutto i costruttori)
#TODO M: Se serve: override __repr__ di tutte le classi?
#TODO M: aggiungere zc al costruttore di Service

import copy
from ipaddress import IPv4Address
from enum import Enum, IntEnum
from forch.forch_tools import raise_error
from forch.forch_utils_zabbix import ZabbixNode, ZabbixController

from forch.forch_tools import get_lst
import os
import json

# from forch.forch_utils_slp import SLPController

#from https://docs.python.org/3/library/enum.html
class MetricType(Enum):
  CPU = "CPU utilization"
  RAM = "Memory utilization"

class MeasurementRetrievalMode(IntEnum):
  SERVICE = 1
  NODE = 2
  METRIC = 3

class Service:
  __zc = None
    
  class _ServiceNode:
    class _Metric:
      def __init__(self, id="", m_type=MetricType.CPU, timestamp="", value="", unit=""):
        self.__id = id
        self.__type = m_type
        self.__timestamp = timestamp
        self.__value = value
        self.__unit = unit

      def __eq__(self, obj):
        if isinstance(obj, self.__class__):
          return self.__id == obj.get_id()
        return False
      
      def get_id(self):
        return self.__id
      def set_id(self, id):
        self.__id = id
        
      def get_name(self):
        return self.__name
      def set_name(self, name):
        self.__name = name
        
      def get_timestamp(self):
        return self.__timestamp
      def set_timestamp(self, timestamp):
        self.__timestamp = timestamp
        
      def get_value(self):
        return self.__value
      def set_value(self, value):
        self.__value = value
      
      def get_unit(self):
        return self.__unit
      def set_unit(self, unit):
        self.__unit = unit
        
      def update(self, measurements_dict):
        # measurements_dict is expected to be a dictionary formatted as {'30254': {'node_id': '10313', 'metric_id': '30254', 'metric_name': 'CPU utilization', 'timestamp': '0', 'value': '0', 'unit': '%'}}
        m_id = self.get_id()
        assert m_id in measurements_dict, "Measurement of metric {} is not in provided measurements!".format(m_id)
        self.set_timestamp(measurements_dict[m_id]["timestamp"])
        self.set_value(measurements_dict[m_id]["value"])
        if self.get_unit() == "":
          self.set_unit(measurements_dict[m_id]["unit"])
        
        
      # def retrieve_measurements(self): # TODO G: tenere questo metodo o no?
      #   # method to refresh the value of a single metric
      #   measurements = Service.__zc.get_measurements_by_item_id(self.get_id()) # TODO G: si fa così ad invocare __zc da dentro una sottoclasse?
      #   # populate the data structure
      #   m_id = self.get_id()
      #   if m_id in measurements:
      #     metric.set_timestamp(measurements[m_id]["timestamp"])
      #     metric.set_value(measurements[m_id]["value"])
      #     metric.set_unit(measurements[m_id]["unit"]) # TODO G: inutile settare ogni volta le unità (?)
      #   else:
      #     # TODO G: come gestire il caso in cui un nodo abbia una metrica che però non compare tra le misure? è possibile?
      #     pass      
  
    # 0xffff = slp.SLP_LIFETIME_MAXIMUM
    def __init__(self, id="", name="", available=False, ipv4=None, port=None, path="", lifetime=0xffff, metrics_list=[]):
      assert isinstance(ipv4, IPv4Address) and ipv4 != None, "Parameter ipv4 must me an IPv4Address!"
      
      self.__id = id
      self.__name = name
      self.__available = available
      self.__ip = ipv4
      self.__port = port
      self.__path = path
      self.__lifetime = lifetime
      # self.__metrics_list = get_lst(metric) # TODO M: da rivedere
      # "metrics" is expected to be formatted as { metric_id: metric_type }
      self.__metrics_list = metrics_list

    def __eq__(self, obj):
      if isinstance(obj, self.__class__):
        return self.__id == obj.get_id()
      return False
      
    def get_id(self):
 	    return self.__id 
    def set_id(self, id):
      self.__id = id

    def get_name(self):
      return self.__name    
    def set_name(self, name):
      self.__name = name

    def get_available(self):
      return self.__available    
    def set_available(self, available):
      self.__available = available

    def get_ip(self):
      return self.__ip
    def set_ip(self, ipv4):
      assert isinstance(ipv4, IPv4Address), "Parameter ipv4 must me an IPv4Address!"
      self.__ip = ipv4

    def get_port(self):
      return self.__port
    def set_port(self, port):
      self.__port = port

    def get_path(self):
      return self.__path
    def set_path(self, path):
      self.__path = path

    def get_lifetime(self):
      return self.__lifetime
    def set_lifetime(self, lifetime):
      self.__lifetime = lifetime

    def get_metrics_list(self):
      return self.__metrics_list
      
    #TODO G: Valutare setter di self.__metrics_list
    
    def get_metric_by_name(self, m_type):
      assert isinstance(m_type, MetricType), "Parameter m_type must be a MetricType!"
      #return next((metric for metric in self.__metric_list if metric.get_name() == m_type), None) # not used because readability    
      for metric in self.get_metrics_list():
        if metric.get_name() == m_type:
          return metric
      return None
      
    # def retrieve_measurements(self): # TODO G: tenere questo metodo o no?
    #   # method to refresh the value of all metrics of a node
    #   measurements = Service.__zc.get_measurements_by_item_id([m.get_id() for m in self.get_metrics_list()]) # TODO G: si fa così ad invocare __zc da dentro una sottoclasse?
    #   # populate the data structure
    #   for metric in node.get_metrics_list():
    #     m_id = metric.get_id()
    #     if m_id in measurements:
    #       metric.set_timestamp(measurements[m_id]["timestamp"])
    #       metric.set_value(measurements[m_id]["value"])
    #       metric.set_unit(measurements[m_id]["unit"]) # TODO G: inutile settare ogni volta le unità (?)
    #     else:
    #       # TODO G: come gestire il caso in cui un nodo abbia una metrica che però non compare tra le misure? è possibile?
    #       pass

  def __init__(self, name="", protocol="", node_list=[], id="", category="", descr=""):
    for node in node_list:
      assert isinstance(node, self._ServiceNode), "Parameter node_list must be a list of ServiceNode!"

    self.__name = name
    self.__protocol = protocol
    self.__node_list = node_list
    self.__id = id
    self.__category = category
    self.__descr = descr
 
  def __eq__(self, obj):
    if isinstance(obj, self.__class__):
      return self.__id == obj.get_id()
    return False

  def get_name(self):
    return self.__name
  def set_name(self, name):
    self.__name = name

  def get_protocol(self):
    return self.__protocol
  def set_protocol(self, protocol):
    self.__protocol = protocol

  def get_node_list(self):
    return self.__node_list
  # def __set_node_list(self, node_list):
  #   self.__node_list = node_list

  def get_id(self):
    return self.__id
  def set_id(self, id):
    self.__id = id

  def get_category(self):
    return self.__category
  def set_category(self, category):
    self.__category = category

  def get_descr(self):
    return self.__descr
  def set_descr(self, descr):
    self.__descr = descr

  # This is the convergence point between Zabbix and SLP
  def add_node(self, ipv4=None, port=None, path="", lifetime=0xffff):
    assert self.__zc != None, "Zabbix controller not assigned yet. Call before Service.set_zabbix_controller()"
    assert isinstance(ipv4, list) and ipv4 != None, "Parameter node_ip_list must be a list of IPv4Address objects!"

    node = self.__zc.get_node_by_ip(ipv4)
    node_dict = node.to_dict()
    node_dict["available"] = node_dict["available"] == "1"
    
    # create metrics list for this node
    m_list = [ self._ServiceNode._Metric(id=self.__zc.get_item_id_by_node_and_item_name(node_dict["node_id"], elem.value), m_type=elem) for elem in MetricType ]
    
    # instatiate new ServiceNode and append it to node list
    self.__node_list.append(self._ServiceNode(id=node_dict["node_id"], name=node_dict["name"], available=node_dict["available"], ipv4=ipv4, port=port, path=path, lifetime=lifetime, metrics_list=m_list))
       
    # TODO M: ritornare qualcosa?

  # TODO M: se questo metodo è usato solo da SLPController, decidere se tenerlo qui o metterlo li
  # Useful links:
  # https://stackoverflow.com/questions/9835762/how-do-i-find-the-duplicates-in-a-list-and-create-another-list-with-them
  # https://stackoverflow.com/questions/9542738/python-find-in-list
  @classmethod
  def aggregate_nodes_of_equal_services(cls, service_list): #TODO M: trovare nome migliore
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
        ret_list[ret_list.index(srvc)] = cls(name=srvc.get_name(), protocol=srvc.get_protocol(), node_list=new_node_list, id=srvc.get_id(), category=srvc.get_category(), descr=srvc.get_descr())
    return ret_list

  @staticmethod
  def get_zabbix_controller():
    return Service.__zc
  @staticmethod
  def set_zabbix_controller(zc):
    assert isinstance(zc, ZabbixController), "Parameter zc must be a ZabbixController object!"
    Service.__zc = zc

  def get_node_by_metric(self, m_type=MetricType.CPU, check="min"):
    metric_list = []
    
    #get list of a specified metric from the node list
    for node in self.__node_list:
      metric = node.get_metric_by_name(m_type)
      if metric != None:
        metric_list.append(metric)
        
    if not metric_list: #if list is empty
      return None
    
    #Sorting metrics by value (https://docs.python.org/3/howto/sorting.html)
    if check == "min":
      # res_metric = sorted(metric_list, key=lambda metric: metric.get_value())[0]
      res_metric = min(metric_list, key=lambda metric: metric.get_value())
    elif check == "max":
      # res_metric = sorted(metric_list, key=lambda metric: metric.get_value())[-1]
      res_metric = max(metric_list, key=lambda metric: metric.get_value())
    else:
      return None
      
    #find the node that owns the result metric and return it
    for node in self.__node_list:
      #in questo if ci fa comodo l'override di __eq__ fatto nella classe Metric
      if res_metric == node.get_metric_by_name(m_type):
        return node
        
  def retrieve_measurements(self, mode=MeasurementRetrievalMode.SERVICE):
    assert self.__zc != None, "Zabbix controller not assigned yet. Call before Service.set_zabbix_controller()"
    assert isinstance(mode, MeasurementRetrievalMode), "Parameter mode must be a MeasurementRetrievalMode!"
    # check retrieval mode
    if mode == MeasurementRetrievalMode.SERVICE:
      # retrieve all measurements (of the defined metrics) of all nodes associated to this Service
      # get list of known nodes (it will be used multiple times)
      node_list = self.get_node_list()
      # retrieve all measurements for all nodes for all defined metric types
      # this returns a dictionary formatted as {'30254': {'node_id': '10313', 'metric_id': '30254', 'metric_name': 'CPU utilization', 'timestamp': '0', 'value': '0', 'unit': '%'}}
      measurements = self.__zc.get_measurements_by_node_list([node.get_id() for node in node_list], item_name_list=[item.value for item in MetricType])
      # populate the data structure
      for node in node_list:
        for metric in node.get_metrics_list():
          metric.update(measurements)
    elif mode == MeasurementRetrievalMode.NODE:
      # refresh the value of all metrics of a node
      for node in self.get_node_list(): 
        measurements = self.__zc.get_measurements_by_item_id([m.get_id() for m in node.get_metrics_list()])
        # populate the data structure
        for metric in node.get_metrics_list():
          metric.update(measurements)
    elif mode == MeasurementRetrievalMode.METRIC:
      # refresh the value of a single metric
      for node in self.get_node_list():
        for metric in node.get_metrics_list():
          measurements = self.__zc.get_measurements_by_item_id(metric.get_id())
          metric.update(measurements)
    else:
      # should never happen
      pass

  @classmethod
  def parse_json_services_file(cls, json_services_file):
    assert isinstance(json_services_file, str), "Parameter json_service_file must be a string!"
    assert os.path.isfile(json_services_file), '"{}" is not a file or it doesn\'t exist.'.format(json_services_file)

    services_list = []
    paths_list = []
    lifetimes_list = []

    with open(json_services_file, 'r') as f:
      jsonDict = json.load(f)     

    for as_a_service_type in jsonDict:
      for service_id in jsonDict[as_a_service_type]:
        name = jsonDict[as_a_service_type][service_id]['name']
        protocol = jsonDict[as_a_service_type][service_id]['protocol']
        descr = jsonDict[as_a_service_type][service_id]['descr']

        services_list.append(cls(name=name, protocol=protocol, id=service_id, category=as_a_service_type, descr=descr))
        paths_list.append(jsonDict[as_a_service_type][service_id]['path'])
        lifetimes_list.append(int(jsonDict[as_a_service_type][service_id]['lifetime']))

    return (services_list, paths_list, lifetimes_list)

if __name__ == "__main__":
  # def truncated_str(elem):
  #   s = str(elem)
  #   if len(s) < 600:
  #     return s
  #   else:
  #     return s[:600] + " [...]"

  # instantiate Zabbix controller
  zc = ZabbixController()

  Service.set_zabbix_controller(zc)