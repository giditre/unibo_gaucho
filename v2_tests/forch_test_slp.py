import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.absolute()))
print(sys.path)
# Path(__file__) is the path to the current file, .parent is the file's directory, .parent again for the parent directory, etc.

from forch.forch_utils_service import Service
from forch.forch_utils_slp import SLPFactory
from forch.forch_utils_zabbix import ZabbixController
from ipaddress import IPv4Address
import asyncio

ua = SLPFactory.create_UA()
fnd = ua.find_all_services()
print(fnd)

# print([ann.__dict__ == fnd[fnd.index(ann)].__dict__ for ann in srv_list])

# asyncio.get_event_loop().run_forever()

