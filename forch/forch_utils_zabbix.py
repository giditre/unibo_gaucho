import logging
from logging.config import fileConfig
fileConfig("logging_config.ini")
logger = logging.getLogger("fuzabbix")
logger.info("Load {} with {}".format(__name__, logger))

import json
from pyzabbix import ZabbixAPI
from ipaddress import IPv4Address
from enum import Enum

class MesurementsFields(Enum):
  NODE_ID = "node_id"
  ID = "metric_id"
  NAME = "metric_name"
  TIMESTAMP = "timestamp"
  VALUE = "value"
  UNIT = "unit"

class ZabbixNode:
  def __init__(self, node_id="", node_name="", node_ipv4=None, is_available=""):
    self.__node_id = node_id
    self.__node_name = node_name
    self.__node_ipv4 = IPv4Address(node_ipv4)
    self.__is_available = is_available

  def get_node_id(self):
    return self.__node_id

  def set_node_id(self, node_id) :
    self.__node_id = node_id

  def get_node_name(self):
    return self.__node_name

  def set_node_name(self, node_name) :
    self.__node_name = node_name

  def get_node_ipv4(self):
    return self.__node_ipv4

  def set_node_ipv4(self, node_ipv4) :
    self.__node_ipv4 = node_ipv4

  def get_is_available(self):
    return self.__is_available

  def set_is_available(self, is_available) :
    self.__is_available = is_available

  def __repr__(self):
    return "ZabbixNode ID {} - name {} - IPv4 {} - available {}".format(
      self.__node_id, self.__node_name, self.__node_ipv4, self.__is_available)

  def to_dict(self):
    return {
      "node_id": self.__node_id,
      "node_name": self.__node_name,
      "node_ipv4": self.__node_ipv4,
      "is_available": self.__is_available
    }

  def to_json(self):
    return json.dumps( { k: str(v) for k, v in self.to_dict().items() } )

  @staticmethod
  def validate_node_id(node):
    assert isinstance(node, (ZabbixNode, str)), "Nodes must be provided as ZabbixNode or str, not {}".format(type(node))
    if isinstance(node, ZabbixNode):
      # "node" is a ZabbixNode object and we need to extract the ID
      return node.get_node_id()
    elif isinstance(node, str):
      # "node" is already an ID
      return node
    else:
      raise TypeError # TODO G: rischiamo davvero di arrivare qui?

class ZabbixController:
  # Used as private static final dict
  class _ItemFields(Enum):
    hostid = MesurementsFields.NODE_ID.value
    itemid = MesurementsFields.ID.value
    name = MesurementsFields.NAME.value
    lastclock = MesurementsFields.TIMESTAMP.value
    lastvalue = MesurementsFields.VALUE.value
    units = MesurementsFields.UNIT.value

  __zc = None

  def __init__(self, url, user, password):
    self.__url = url
    self.__user = user
    self.__password = password
    self.__zapi = ZabbixAPI(url=self.__url, user=self.__user, password=self.__password)

  def __repr__(self):
    return "ZabbixController on URL {} with user {}".format(self.__url, self.__user)

  @classmethod
  def get_instance(cls):
    if cls.__zc is None:
      cls.__zc = cls(url='http://localhost/zabbix/', user='Admin', password='zabbix') # TODO M: fare parse dati costruttore prendendoli da qualche parte. JSON, __init__.py, ecc...
    return cls.__zc

  def get_url(self):
    return self.__url

  def get_nodes(self, server_name="Zabbix Server"):
    # fields=["hostid", "name", "available"]

    # z_node_list = [ ZabbixNode( *[ h[f] for f in fields ] ) for h in self.zapi.host.get(search={"name": server_name}, excludeSearch=True) ]

    z_node_list = []

    for h in self.__zapi.host.get(search={"name": server_name}, excludeSearch=True):
      # print(h)

      h_id = h["hostid"]
      h_name = h["name"]
      h_avail = h["available"]
      
      h_ip = None
      for i in self.__zapi.hostinterface.get(hostids= h_id):
        h_ip = i["ip"]
        break

      z_node = ZabbixNode(h_id, h_name, h_ip, h_avail)
      z_node_list.append(z_node)

    return z_node_list

  def get_node_by_ip(self, ip):
    if not isinstance(ip, IPv4Address):
      ip = IPv4Address(ip)
    for zn in self.get_nodes():
      if zn.get_node_ipv4() == ip:
        return zn
    return None

  def get_item_id_by_node_and_item_name(self, node, item_name): # TODO G: maybe find better name
    node_id = ZabbixNode.validate_node_id(node)
    item_list = self.__zapi.item.get(hostids=node_id, search={"name": item_name})
    if len(item_list) == 1:
      return item_list[0]["itemid"]
    else:
      # TODO G: how to handle this case?
      # print(item_list)
      raise ValueError 

  # def get_item_id_by_node(self, node):
  #   node_id = ZabbixNode.validate_node_id(node)


  def get_measurements_by_node(self, node, item_name_list=[]):
    return self.get_measurements_by_node_list([node], item_name_list)

  def get_measurements_by_node_list(self, node_list, item_name_list=[]):
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

  def get_measurements_by_item_id(self, item_id):
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

  logger.info("Instantiate ZabbixController")
  zc = ZabbixController.get_instance()

  print("List of all known nodes:")
  print(zc.get_nodes())
  print()

  # node_ip = "192.168.10.120"
  # print("Details on node having address {}:".format(node_ip))
  # node1 = zc.get_node_by_ip(node_ip)
  # print("As a string: ", node1)
  # print("As a dict: ", node1.to_dict())
  # print("As a JSON: ", node1.to_json())
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