from pyzabbix import ZabbixAPI
import json

from datetime import datetime

zapi = ZabbixAPI(url='http://localhost/zabbix/', user='Admin', password='zabbix')

fognodes_dict = { h["hostid"] : h for h in zapi.host.get(search={"name": "Zabbix Server"}, excludeSearch=True) }
#print(json.dumps(fognodes_dict, indent=2))

hostname_list = [ fognodes_dict[h]["name"] for h in fognodes_dict ]
print(hostname_list)

for h_id in fognodes_dict:
  for item in zapi.item.get(filter={"hostid": h_id}, search={"name": "*utilization*"}, searchWildcardsEnabled=True):
    lastclock = int(item["lastclock"])
    if lastclock == 0:
      continue
    print(item["hostid"], datetime.fromtimestamp(lastclock), item["itemid"], item["name"], item["lastvalue"], item["units"])

#item = zapi.item.get(itemids=30254)[0]
#print(item)
#print(item["hostid"], datetime.fromtimestamp(int(item["lastclock"])), item["itemid"], item["name"], item["lastvalue"], item["units"])

