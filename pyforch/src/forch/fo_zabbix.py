#TODO G: create/complete docstrings and declare variables types statically using hints


# This import allows to hint custom classes and to use | instead of Union[]
# TODO: remove it when Python 3.10 will be used
from __future__ import annotations
import logging
from typing import List

# from logging.config import fileConfig
# from pathlib import Path
# fileConfig(str(Path(__file__).parent.joinpath("logging.conf")))
# logger = logging.getLogger("fuzabbix")
# logger.info("Load {} with {}".format(__name__, logger))


# class _NullHandler(logging.Handler):
#     def emit(self, record):
#         pass

# logger = logging.getLogger(__name__)
# logger.addHandler(_NullHandler())


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

import json
from pyzabbix import ZabbixAPI
from ipaddress import IPv4Address
from enum import Enum

class MetricType(Enum):

  CPU = "CPU utilization"
  RAM = "Memory utilization"
  #TOT_RAM = "Total memory"
  #FREE_SWAP = "Free swap space in %"
  #N_THREADS = "Number of threads"
  #N_PROC = "Number of processes"
  #SYS_NAME = "System name"
  #SYS_DESCR = "System description"
  #SYS_UPTIME = "Uptime"
  #OS_ARCH = "Operating system architecture"

class ZabbixNodeFields(Enum):
  ID = "id"
  NAME = "name"
  IPv4 = "ipv4"
  AVAILABLE = "is_available"

class MeasurementFields(Enum):
  NODE_ID = "node_id"
  ID = "metric_id"
  NAME = "metric_name"
  TIMESTAMP = "timestamp"
  VALUE = "value"
  UNIT = "unit"

class ZabbixNode:
  def __init__(self, *, node_id:str="", node_name:str="", node_ipv4:IPv4Address|None=None, is_available:str=""):
    self.__node_id: str = node_id
    self.__node_name: str = node_name
    self.__node_ipv4: IPv4Address = IPv4Address(node_ipv4)
    self.__is_available: str = is_available

  def get_node_id(self):
    return self.__node_id

  def set_node_id(self, node_id:str) :
    self.__node_id = node_id

  def get_node_name(self):
    return self.__node_name

  def set_node_name(self, node_name:str) :
    self.__node_name = node_name

  def get_node_ipv4(self):
    return self.__node_ipv4

  def set_node_ipv4(self, node_ipv4:IPv4Address) :
    self.__node_ipv4 = node_ipv4

  def get_is_available(self):
    return self.__is_available

  def set_is_available(self, is_available:str) :
    self.__is_available = is_available

  def __repr__(self):
    return "ZabbixNode ID {} - name {} - IPv4 {} - available {}".format(
      self.__node_id, self.__node_name, self.__node_ipv4, self.__is_available)

  def to_dict(self):
    return {
      ZabbixNodeFields.ID.value: self.__node_id,
      ZabbixNodeFields.NAME.value: self.__node_name,
      ZabbixNodeFields.IPv4.value: self.__node_ipv4,
      ZabbixNodeFields.AVAILABLE.value: self.__is_available
    }

  def to_json(self):
    return json.dumps(self.to_dict(), default=lambda x: str(x)) # the default function is applied when an object is not JSON serializable, e.g., IPv4Address

  @staticmethod
  def validate_node_id(node:ZabbixNode|str):
    assert isinstance(node, (ZabbixNode, str)), f"Nodes must be provided as ZabbixNode or str, not {type(node)}"
    if isinstance(node, ZabbixNode):
      # "node" is a ZabbixNode object and we need to extract the ID
      return node.get_node_id()
    else:
      # "node" is already an ID
      return node

class ZabbixAdapter(object):
  # Used as private static final dict
  class _ItemFields(Enum):
    hostid = MeasurementFields.NODE_ID.value
    itemid = MeasurementFields.ID.value
    name = MeasurementFields.NAME.value
    lastclock = MeasurementFields.TIMESTAMP.value
    lastvalue = MeasurementFields.VALUE.value
    units = MeasurementFields.UNIT.value

  __key = object()
  __zc = None

  def __init__(self, *, key=None, url, user, password):
    assert key == self.__class__.__key, "There can only be one {0} object and it can only be accessed with {0}.get_instance()".format(self.__class__.__name__)
    self.__url = url
    self.__user = user
    self.__password = password
    # self.__zapi = ZabbixAPI(url=self.__url, user=self.__user, password=self.__password) # Python3.6
    self.__zapi:ZabbixAPI = ZabbixAPI(self.__url)
    self.__zapi.login(user=self.__user, password=self.__password)

  def __repr__(self):
    return "ZabbixAdapter on URL {} with user {}".format(self.__url, self.__user)

  @classmethod
  def get_instance(cls):
    if cls.__zc is None:
      cls.__zc = cls(key=cls.__key, url='http://localhost/zabbix/', user='Admin', password='zabbix') # TODO G: parse values from configfile
    return cls.__zc

  def get_url(self):
    return self.__url

  def get_nodes(self, server_name:str="Zabbix Server") -> List[ZabbixNode]:
    # fields=["hostid", "name", "available"]

    # z_node_list = [ ZabbixNode( *[ h[f] for f in fields ] ) for h in self.zapi.host.get(search={"name": server_name}, excludeSearch=True) ]

    z_node_list = []

    for h in self.__zapi.host.get(search={"name": server_name}, excludeSearch=True):
      # print(h)

      h_id = h["hostid"]
      h_name = h["name"]
      h_avail = h["available"]
      
      # TODO G: should we handle the case in which a host has more than one interface? Or is it better to suppose that each node exposes only a single net iface to the fog system?
      h_ip = None
      for i in self.__zapi.hostinterface.get(hostids= h_id):
        h_ip = i["ip"]
        break

      z_node = ZabbixNode(node_id=h_id, node_name=h_name, node_ipv4=h_ip, is_available=h_avail)
      z_node_list.append(z_node)

    return z_node_list

  def get_node_by_ip(self, ip:IPv4Address):
    for zn in self.get_nodes():
      if zn.get_node_ipv4() == ip:
        return zn
    return None

  def get_item_id_by_node_and_item_name(self, node, item_name): # TODO G: maybe find better (shorter) name
    node_id = ZabbixNode.validate_node_id(node)
    item_list = self.__zapi.item.get(hostids=node_id, search={"name": item_name})
    if len(item_list) == 1:
      return item_list[0]["itemid"]
    else:
      # TODO G: how to handle this case?
      # item_list = self.__zapi.item.get(hostids=node_id)
      # print(item_list)
      raise ValueError

  # def get_item_id_by_node(self, node):
  #   node_id = ZabbixNode.validate_node_id(node)


  def get_measurements_by_node(self, node, item_name_list=[]):
    return self.get_measurements_by_node_list([node], item_name_list=item_name_list)

  def get_measurements_by_node_list(self, node_list, *, item_name_list=[]):
    node_id_list = []
    for node in node_list:
      node_id = ZabbixNode.validate_node_id(node)
      node_id_list.append(node_id)

    measurements = {}

    if not item_name_list:
      measurements.update( { item["itemid"]: { f.value: item[f.name] for f in self._ItemFields } for item in self.__zapi.item.get(hostids=node_id_list) } )

    else:
      for item_name in item_name_list:
        measurements.update( { item["itemid"]: { f.value: item[f.name] for f in self._ItemFields } for item in self.__zapi.item.get(hostids=node_id_list, search={"name": item_name}, searchWildcardsEnabled=True) } )

    return measurements

  def get_measurements_by_item_id(self, item_id:str):
    return self.get_measurements_by_item_id_list([item_id])

  def get_measurements_by_item_id_list(self, item_id_list):
    measurements = { item["itemid"]: { f.value: item[f.name] for f in self._ItemFields } for item in self.__zapi.item.get(itemids=item_id_list) }
    return measurements


if __name__ == "__main__":
  def truncated_str(elem):
    s = str(elem)
    if len(s) < 600:
      return s
    else:
      return s[:600] + " [...]"

  logger.info("Instantiate ZabbixAdapter")
  zc = ZabbixAdapter.get_instance()

  print("List of all known nodes:")
  print(zc.get_nodes())
  print()

  node_ip = "192.168.64.123"
  print("Details on node having address {}:".format(node_ip))
  node1 = zc.get_node_by_ip(IPv4Address(node_ip)) # TODO G: add an handler that manages the return None case
  print("As a string: ", node1)
  print("As a dict: ", node1.to_dict())
  print("As a JSON: ", node1.to_json())
  # node_ip = "192.168.10.123"
  # print("Details on node having address {}:".format(node_ip))
  # node2 = zc.get_node_by_ip(node_ip)
  # print("As a string: ", node2)
  # print("As a dict: ", node2.to_dict())
  # print("As a JSON: ", node2.to_json())
  # print()

  # print("Different ways to get measurements:")
  # print("--- by node, e.g.: get_measurements_by_node(node1)")
  # print(truncated_str(zc.get_measurements_by_node(node1)))
  # print("--- by node list, e.g.: get_measurements_by_node_list([node1, node2])")
  # print(truncated_str(zc.get_measurements_by_node_list([node1, node2])))
  # print("--- by node or node list with item names, e.g.: get_measurements_by_node_list([node1, node2], [\"CPU utilization\", \"Memory utilization\"])")
  # print(truncated_str(zc.get_measurements_by_node_list([node1, node2], ["CPU utilization", "Memory utilization"])))
  # print("--- by item ID, e.g.: get_measurements_by_item_id(\"30254\")")
  # print(truncated_str(zc.get_measurements_by_item_id("30254")))
  # print("--- by item ID list, e.g.: get_measurements_by_item_id_list([\"30251\",\"31007\"])")
  # print(truncated_str(zc.get_measurements_by_item_id_list(["30251","31007"])))
  # print()

  # print("Getting item ID by node and item name, e.g.: get_item_id_by_node_and_item_name(node1, \"CPU utilization\")")
  # print(zc.get_item_id_by_node_and_item_name(node1, "CPU utilization"))