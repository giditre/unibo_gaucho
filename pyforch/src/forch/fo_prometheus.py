from __future__ import annotations
import configparser
from typing import List
from prometheus_client import Gauge, start_http_server
import logging
from ipaddress import IPv4Address
from enum import Enum
import psutil
import json
import requests
from prometheus_client.parser import text_string_to_metric_families
import time
import threading
import configparser
from pathlib import Path
import subprocess
from .fo_zabbix import MetricType

# setting the config file
config = configparser.ConfigParser()
config.read('/home/gaucho/unibo_gaucho-master/main/src/main/main.ini') #--fix the path

# configuration of the logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class PrometheusNodeFields(Enum):

  ID = "id"
  NAME = "name"
  IPv4 = "ipv4"
  PORT = "port"
  UPT = "update_time"
  AVL = "is_available"

class MeasurementFields(Enum):

  NODE_ID = "node_id"
  ID = "metric_id"
  NAME = "metric_name"
  TIMESTAMP = "timestamp"
  VALUE = "value"
  UNIT = "unit"

class PrometheusNode:

  # dictionary that holds the mesurements of the node
  __prometheus_measurements = { 

    'CPU': [],
    'RAM': 0,
    'DISK': 0,
    'NET': [] 
  
  }

  # list of item ids that univocally represent a measurement
  __item_id_list = []

  def __init__(self, *, node_id:str="", node_name:str="", node_ipv4:IPv4Address|None=None, node_port:int=0, is_available:str="", update_period:int=0):
    
    self.__node_update_period: int = update_period
    self.__node_id: str = node_id
    self.__node_name: str = node_name
    self.__node_ipv4: IPv4Address = IPv4Address(node_ipv4)
    self.__node_port: int = node_port
    self.__is_available: str = is_available

    #building the list of item id for the node
    self.build_item_id_list()

  def build_item_id_list(self):

    for key in self.__prometheus_measurements.keys():

      self.__item_id_list.append(self.__node_id + key)

  #definitions of getters and setters

  def get_node_id(self):

    return self.__node_id

  def set_node_id(self, node_id:str):

    self.__node_id = node_id

  def get_node_name(self):

    return self.__node_name

  def set_node_name(self, node_name:str):

    self.__node_name = node_name

  def get_node_ipv4(self):

    return self.__node_ipv4

  def set_node_ipv4(self, node_ipv4:IPv4Address):

    self.__node_ipv4 = node_ipv4

  def get_is_available(self):

    return self.__is_available

  def set_is_available(self, is_available:str):

    self.__is_available = is_available

  def set_node_update_period(self, node_update_period:int):

    self.__node_update_period = node_update_period

  def get_node_update_period(self):

    return self.__node_update_period

  def get_node_port(self):

    return self.__node_port

  def set_node_port(self, node_port:int):

    self.__node_port = node_port

  def get_node_item_id_list(self):

    return self.__item_id_list

  def __repr__(self) -> str:

    """"
    Represents in a readable way the caracterisctics of the node.

    Args:
      .

    Returns:
      String.
    """

    return f"PrometheusNode id {self.__node_id} - name {self.__node_name} - ipv4 {self.__node_ipv4} - port {self.__node_port} - is avaiable {self.__is_available} - update period {self.__node_update_period}"
  
  def to_dict(self) -> dict:

    """"
    Returns a dictionary that contains the characteristics of the node.

    Args:
      .

    Returns:
      dict.
    """

    return {

      PrometheusNodeFields.ID.value: self.__node_id,
      PrometheusNodeFields.NAME.value: self.__node_name,
      PrometheusNodeFields.IPv4.value: self.__node_ipv4,
      PrometheusNodeFields.PORT.value: self.__node_port,
      PrometheusNodeFields.UPT.value: self.__node_update_period,
      PrometheusNodeFields.AVL.value: self.__is_available

    }

  def to_json(self) -> str:

    """"
    Transforms the dictionary into the json format.

    Args:
      .

    Returns:
      A json formatted String.
    """

    return json.dumps(self.to_dict(), default=lambda x: str(x))

  @staticmethod
  def validate_node_id(node:PrometheusNode|str=None) -> PrometheusNode|str:

    """"
    Given the node it returns the associated id; if a node id is provided instead of a node, it returns the id itself.

    Args:
      .

    Returns:
      node|node_id.
    """

    assert isinstance(node, (PrometheusNode, str)), f"Nodes must be provided as PrometheusNode or str, not {type(node)}"

    if isinstance(node, PrometheusNode):

      return node.get_node_id()

    else:

      return node

class PrometheusApi(object):

  class _ItemFields(Enum):

    hostid = MeasurementFields.NODE_ID.value
    itemid = MeasurementFields.ID.value
    name = MeasurementFields.NAME.value
    lastclock = MeasurementFields.TIMESTAMP.value
    lastvalue = MeasurementFields.VALUE.value
    units = MeasurementFields.UNIT.value

  #type of variable used by prometheus to keep track of measurements
  __SYSTEM_USAGE = Gauge('system_usage', 'Hold current system resource usage', ['resource_type']) #--introduce also the unit

  __key = object()
  __pc = None

  def __init__(self, *, key=None, url:IPv4Address|None=None, user:str="", password:str=""):
    
    assert key == self.__class__.__key, f"There can only be one {self.__class__.__name__} object and it can only be accessed with {self.__class__.__name__}.get_instance()"
    #--implement a login profile (?)
    self.__url = url
    self.__user = user
    self.__password = password

  # makes it sure that only one instance of this class can be created
  @classmethod
  def get_instance(cls) -> PrometheusApi:

    if cls.__pc is None:

      cls.__pc = cls(key=cls.__key, url="", user="", password="", )
    
    return cls.__pc

  def expose_measurements(self, *, port:int=2412): #--how to check it is called just once

    """"
    Starts a WSGI server for prometheus measurements as a daemon thread on the given port, then it schedules a thread that collects the measurements each __node_update_period.

    Args:
      port.

    Returns:
      .
    """

    logger.debug("Starting the prometheus server...")
    start_http_server(port)

    thread = threading.Thread(target=self.schedule)
    thread.start()

  def schedule(self):

    """"
    Definition of the scheduler, has to update the measurements each upt_period.

    Args:
      .

    Returns:
      .
    """

    upt_p = int(self.get_node_by_ip(url=IPv4Address(subprocess.getoutput("hostname -I").split()[0])).get_node_update_period())

    while True:

      self.update_measurements() 
      time.sleep(upt_p)

  def update_measurements(self):

    """"
    Atomic function that update the Gauge variable that is taken by the prometheus server.

    Args:
      .

    Returns:
      .
    """

    logger.debug("Updating measurements...")

    for i in range(len(psutil.cpu_percent(interval=1, percpu=True))):

      self.__SYSTEM_USAGE.labels(f'CPU {i}').set(psutil.cpu_percent(interval=1, percpu=True)[i])

    self.__SYSTEM_USAGE.labels('rx').set(psutil.net_io_counters().bytes_recv)

    self.__SYSTEM_USAGE.labels('tx').set(psutil.net_io_counters().bytes_sent)
      
    self.__SYSTEM_USAGE.labels('RAM').set(psutil.virtual_memory().percent)

    self.__SYSTEM_USAGE.labels('DISK').set(psutil.disk_usage('/').percent)    
  
  @staticmethod
  def retrieve_measurements(*, url:IPv4Address=None, port:int=2412) -> dict:

    """"
    Function that is used by the orchestrator to obtain the measurements from a node.
    The format items are returned is dict{item_name: item_value}.

    Args:
      IPv4Address, port.

    Returns:
      {item_name: item_value}.
    """

    assert isinstance(url, IPv4Address), "Parameter url must be an IPv4Address object!" 

    measurements = {}

    data = requests.get(f'http://{url}:{port}/metrics').content.decode('UTF-8')

    for family in text_string_to_metric_families(data):

      for sample in family.samples:

        if sample[0] == 'system_usage':

          measurements.update({sample[1]['resource_type']: sample[2]})

    return measurements

  @staticmethod
  def retrieve_measurement(*, url:IPv4Address=None, port:int=2412, item:MetricType|str="") -> dict: 

    """"
    Function that is used by the orchestrator to obtain a specific measurement from a node.
    If an item is not provided or couldn't be find, the function returns None.

    Args:
      IPv4, port, item.

    Returns:
      {item_name: item_value}.
    """

    assert isinstance(url, IPv4Address), "Parameter url must be an IPv4Address object!" 

    sum = 0.0

    measurements = PrometheusApi.retrieve_measurements(url=url, port=port)

    for key in list(measurements.keys()):

      if type(item) is str:
 
        if not item in key: #--when i retrieve a cpu value, should I do the mean value between different cpus?

          del measurements[str(key)]

      if type(item) is MetricType:
 
        if not item.name in key: #--when i retrieve a cpu value, should I do the mean value between different cpus?

          del measurements[str(key)]

    if len(measurements) > 1:

      for key, value in measurements.items():

        sum += float(value)

      sum = sum / len(measurements)

      measurements.clear()

      measurements.update({'CPU': sum})

    return measurements

  @staticmethod
  def retrieve_measurements_by_item_list(*, url:IPv4Address|None=None, port:int=2412, item_list:List[MetricType]=[]) -> dict:

    """"
    Function that is used by the orchestrator to obtain a list of item_value given the list of item.

    Args:
      IPv4, List[item], port.

    Returns:
      {item_name: item_value}.
    """

    measurements = {}

    for item in item_list:

      measurements.update(PrometheusApi.retrieve_measurement(url=url, port=port, item=item))

    return measurements

  @staticmethod
  def retrieve_measurements_by_item_id_list(*, item_id_list:List[str]=[]) -> dict:

    """"
    Function that is used by the orchestrator to obtain a list of item_value given the list of the id associated to them.

    Args:
      List[item_id].

    Returns:
      {item_name: item_value}.
    """

    measurements = {}

    for id in item_id_list:

      for category in config.sections():
    
        if "fnode" in category:

          if config[category]["id"] in id:

            measurements.update(PrometheusApi.retrieve_measurement(url=IPv4Address(config[category]["address"]), port=config[category]["port"], item=''.join([i for i in id if not i.isdigit()])))

    return measurements

  @staticmethod
  def get_node_by_ip(*, url:IPv4Address=None) -> None|PrometheusNode:

    """"
    Function that returns a a PrometheusNode associated to the given ip.

    Args:
      IPv4.

    Returns:
      PrometheusNode.
    """

    assert isinstance(url, IPv4Address), "Parameter url must be an IPv4Address object!" 

    for prom_node in PrometheusApi.get_nodes():

      if prom_node.get_node_ipv4() == url:

        return prom_node
      
    return None

  @staticmethod
  def get_nodes() -> List[PrometheusNode]:

    """"
    Function that read from a configuration file the different nodes and transforms them in PrometheusNode objects.

    Args:
      .

    Returns:
      List[PrometheusNode].
    """

    p_node_list = []

    for category in config.sections():
    
      if "fnode" in category:

        p_node = PrometheusNode(node_id=config[category]["id"], node_name=category, node_ipv4=config[category]["address"], node_port=config[category]["port"], is_available=PrometheusApi.is_node_available(url=IPv4Address(config[category]["address"]), port=config[category]["port"]), update_period=config[category]["upt_p"])
        p_node_list.append(p_node)

    return p_node_list 

  @staticmethod
  def is_node_available(*, url:IPv4Address=None, port:int=2412) -> bool:

    """"
    Function that checks if a node is reacheable.

    Args:
      IPv4, port.

    Returns:
      Boolean.
    """

    assert isinstance(url, IPv4Address), "Parameter url must be an IPv4Address object!" 

    try:

      requests.get(f'http://{url}:{port}/metrics')

    except requests.exceptions.ConnectionError:
      
      logger.info(f"node on: {url} not available")
      return False

    return True

  @staticmethod
  def get_node_from_node_id_list(*, node_id_list:List[str]=[]) -> dict:

    """"
    Function that returns a dict containing {node_id: node}, given a list of node_ids.

    Args:
      List[node_id].

    Returns:
      dict{node_id: PrometheusNode}.
    """

    node_dict = {}

    for node in PrometheusApi.get_nodes():

      for node_id in node_id_list:

        if node.get_node_id() == node_id:

          node_dict.update({node_id: node})

    return node_dict

  @staticmethod
  def get_il_from_nl(*, node_id_list:List[str]=[]) -> dict:

    """"
    Function that returns the item ids available on each node present on the node id list.

    Args:
      [node_id].

    Returns:
      {node_id: List[item_id]}.
    """

    item_id_dict = {}

    for node_id, node in PrometheusApi.get_node_from_node_id_list(node_id_list=node_id_list).items():

      item_id_dict.update({node_id: node.get_node_item_id_list()})
    
    return item_id_dict

  @staticmethod
  def get_item_id(*, node:PrometheusNode=None, item:MetricType=None) -> str|None:

    """"
    Function that returns the id of the selected item.

    Args:
      PrometheusNode, item.

    Returns:
      item_id|None.
    """

    assert isinstance(node, PrometheusNode), "Parameter node must be a PrometheusNode object!" 

    ii_list = node.get_node_item_id_list()

    for item_id in ii_list:

      if item.name in item_id:

        return item_id #--there can be more than 1 id

    return None

  @staticmethod
  def get_measurements_by_n(*, node:PrometheusNode=None, item_list:List[MetricType]=[]) -> dict:

    """"
    Function that obtains a list of measurements from a given node.

    Args:
      PrometheusNode, List[item].

    Returns:
      Dictionary.
    """

    return PrometheusApi.get_measurements_by_nl(node_ip_list=[node.get_node_ipv4], item_list=item_list)

  @staticmethod
  def get_measurements_by_nl(*, node_ip_list:List[IPv4Address]=[], item_list:List[MetricType]=[]) -> dict:

    """"
    Function that obtains measurements from a list of nodes.

    Args:
      [node_ip], [item].

    Returns:
      {node_id: {node_id: ., item_id: ., item: ., timestamp: ., value: ., unit: .}}.
    """

    measurements = {}

    if not item_list: 

      #--there is for sure a better way to merge the two cases

      for ip in node_ip_list:

        node = PrometheusApi.get_node_by_ip(url=ip)
        meas = PrometheusApi.retrieve_measurements(url=ip, port=node.get_node_port())

        for i, key in enumerate(meas):

          i_id = PrometheusApi.get_item_id(node=node, item=item_list[i])

          #--timestamp should be retrieved and unit is not always %

          measurements.update({i_id: {MeasurementFields.NODE_ID.value: node.get_node_id(), MeasurementFields.ID.value: i_id, MeasurementFields.NAME.value: key, MeasurementFields.TIMESTAMP.value: 'None', MeasurementFields.VALUE.value: meas[key], MeasurementFields.UNIT.value: '%'}}) 

    else:

      # this returns a dictionary formatted as {'30254': {'node_id': '10313', 'item_id': '30254', 'item_name': 'CPU utilization', 'timestamp': '0', 'value': '0', 'unit': '%'}}
 
      for ip in node_ip_list:

        #--there may be a better way to do this instead of retrieving every node and the export the selected one by the given ip

        node = PrometheusApi.get_node_by_ip(url=ip)
        meas = PrometheusApi.retrieve_measurements_by_item_list(url=ip, port=node.get_node_port(), item_list=item_list)

        for i, key in enumerate(meas):

          i_id = PrometheusApi.get_item_id(node=node, item=item_list[i])

          #--timestamp should be retrieved and unit is not always %

          measurements.update({i_id: {MeasurementFields.NODE_ID.value: node.get_node_id(), MeasurementFields.ID.value: i_id, MeasurementFields.NAME.value: key, MeasurementFields.TIMESTAMP.value: 'None', MeasurementFields.VALUE.value: meas[key], MeasurementFields.UNIT.value: '%'}}) 

    return measurements

  @staticmethod
  def get_measurements_by_item_id(*, item_id:str="") -> dict: 

    """"
    Function that obtains measurements of a given item_id.

    Args:
      item_id.

    Returns:
      {node_id: {node_id: ., item_id: ., item_name: ., timestamp: ., value: ., unit: .}}.
    """

    return PrometheusApi.get_measurements_by_item_id_list(item_id_list=[item_id])

  @staticmethod
  def get_measurements_by_item_id_list(*, item_id_list:List[str]=[]) -> dict:

    """"
    Function that obtains measurements of a given list of item id.

    Args:
      List[item_id].

    Returns:
      {node_id: {node_id: ., item_id: ., item_name: ., timestamp: ., value: ., unit: .}}.
    """

    measurements = {}

    meas = PrometheusApi.retrieve_measurements_by_item_id_list(item_id_list=item_id_list)

    for i, key in enumerate(meas):

      #--timestamp should be retrieved and unit is not always %

      measurements.update({item_id_list[i]: {MeasurementFields.NODE_ID.value: ''.join([i for i in item_id_list[i] if i.isdigit()]), MeasurementFields.ID.value: item_id_list[i], MeasurementFields.NAME.value: key, MeasurementFields.TIMESTAMP.value: 'None', MeasurementFields.VALUE.value: meas[key], MeasurementFields.UNIT.value: '%'}}) 

    return measurements