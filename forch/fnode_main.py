import sys
from pathlib import Path
# sys.path.append(str(Path(__file__).parent.parent.absolute()))
# print(sys.path)

from src.forch.forch_utils_service import Service 
from src.forch.forch_utils_slp import SLPFactory
from ipaddress import IPv4Address
import asyncio
import time

sa = SLPFactory.create_SA()
# TODO G: prendere indirizzo IP da interfaccia usata sulla rete fog
srv_list = Service.create_services_from_json(IPv4Address("192.168.64.123"), str(Path(__file__).parent.joinpath("service_example.json").absolute()))
for srv in srv_list:
  print(srv)
  sa.register_service(srv)

asyncio.get_event_loop().run_forever()
