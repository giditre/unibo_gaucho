import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.absolute()))
# print(sys.path)
# Path(__file__) is the path to the current file, .parent is the file's directory, .parent again for the parent directory

from forch.forch_utils_service import Service
from forch.forch_utils_slp import SLPController, SLPAgentType
from forch.forch_utils_zabbix import ZabbixController
from ipaddress import IPv4Address
import asyncio

# SA MAIN
sc = SLPController(SLPAgentType.SA)
zc = ZabbixController()
Service.set_zabbix_controller(zc)

srv_list = Service.create_services_from_json(IPv4Address("127.0.0.1"), str(Path(__file__).parent.joinpath("service_example.json").absolute()))

asyncio.get_event_loop().run_forever()