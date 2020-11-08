import json
from pyzabbix import ZabbixAPI
from ipaddress import IPv4Address

#{"id":id, "name"=name, "available"=available}

class ZabbixNode:
  def __init__(self, node_id="", node_name="", node_ipv4=None, is_available=False):
    self.node_id = node_id
    self.node_name = node_name
    self.node_ipv4 = IPv4Address(node_ipv4)

    if isinstance(is_available, bool):
      self.is_available = is_available
    elif isinstance(is_available, str):
      self.is_available = is_available == "1"
    else:
      raise TypeError("ZabbixNode, parameter is_available has unrecognized value {}".format(is_available))

  def __repr__(self):
    return "ZabbixNode ID {}, name {}, IPv4 {}, available {}".format(self.node_id, self.node_name, self.node_ipv4, self.is_available)

  def to_json(self):
    return json.dumps({
      "node_id": self.node_id,
      "node_name": self.node_name,
      "node_ipv4": str(self.node_ipv4),
      "is_available": self.is_available
    })

  # TODO: getters and setters?

class ZabbixClient: # TODO: ha senso chiamarlo così?
  def __init__(self, url = 'http://localhost/zabbix/', user = 'Admin', password = 'zabbix'):
    self.url = url
    self.user = user
    self.password = password
    self.zapi = ZabbixAPI(url = self.url, user = self.user, password = self.password)

  def __repr__(self):
    return "ZabbixClient on URL {} with user {}".format(self.url, self.user)

  def get_nodes(self, server_name = "Zabbix Server"):
    # fields = ["hostid", "name", "available"]

    # z_node_list = [ ZabbixNode( *[ h[f] for f in fields ] ) for h in self.zapi.host.get(search={"name": server_name}, excludeSearch=True) ]

    z_node_list = []

    for h in self.zapi.host.get(search={"name": server_name}, excludeSearch=True):
      # print(h)

      h_id = h["hostid"]
      h_name = h["name"]
      h_avail = h["available"]
      
      h_ip = None
      for i in self.zapi.hostinterface.get(hostids= h_id):
        h_ip = i["ip"]
        break

      z_node = ZabbixNode(h_id, h_name, h_ip, h_avail)
      z_node_list.append(z_node)

    return z_node_list

  def get_node_by_ip(self, ip=None):
    if not isinstance(ip, IPv4Address):
      ip = IPv4Address(ip)
    for zn in self.get_nodes():
      if zn.node_ipv4 == ip:
        return zn
    return None

#   def get_measurements(self, node_id=None, only_available=True, search_str=""):
#     fields = [ "hostid", "itemid", "name", "lastclock", "lastvalue", "units" ]
#     #node_id_list = None
#     #if node_id is not None and only_available == True:
#     #  node_id_list = "-1"
#     #  if node_id in rsdb.rsdb["nodes"]:
#     #    available = str(rsdb.rsdb["nodes"][node_id]["available"])
#     #    #logger.debug("{} {}".format(node_id, available))
#     #    if available == "1":
#     #      node_id_list = [ node_id ]
#     #elif node_id is None and only_available == True:
#     #  node_id_list = [ h_id for h_id in rsdb.rsdb["nodes"] if rsdb.rsdb["nodes"][h_id]["available"] == "1" ]
#     #  logger.debug("Available hosts: {}".format(node_id_list))
#     node_id_list = [ node_id ]
#     measurements = [ { f: item[f] for f in fields } for item in self.zapi.item.get(filter={"hostid": node_id_list}, search={"name": "*{}*".format(search_str)}, searchWildcardsEnabled=True) ]
#     #logger.debug("MEASUREMENTS : {}".format(measurements))
#     return measurements

if __name__ == "__main__":
  zc = ZabbixClient()
  print(zc.get_nodes())
  print(zc.get_node_by_ip("192.168.10.120").to_json())