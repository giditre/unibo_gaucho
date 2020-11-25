import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.absolute()))
# print(sys.path)
# Path(__file__) is the path to the current file, .parent is the file's directory, .parent again for the parent directory

from src.forch_utils_service import Service
from src.forch_utils_slp import SLPFactory
from src.forch_utils_zabbix import ZabbixController
from ipaddress import IPv4Address
import asyncio

# SA MAIN
sa = SLPFactory.create_SA()
# zc = ZabbixController()
# Service.set_zabbix_controller(zc)

srv_list = Service.create_services_from_json(IPv4Address("127.0.0.1"), str(Path(__file__).parent.joinpath("service_example.json").absolute()))

# GIANLUCAAAAAAAAAAAAAA NON ANDAVA NULLA PERCHé NESSUNO REGISTRAVA I SERVIZI HAHAHAHAHAHA!!!
for srv in srv_list:
  sa.register_service(srv)

ua = SLPFactory.create_UA()
fnd = ua.find_all_services()
print(fnd)

print([ann.__dict__ == fnd[fnd.index(ann)].__dict__ for ann in srv_list])

asyncio.get_event_loop().run_forever()