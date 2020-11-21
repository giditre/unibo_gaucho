import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.absolute()))

from forch.forch_utils_service import Service
from forch.forch_utils_slp import SLPFactory
from ipaddress import IPv4Address

import time

sa = SLPFactory.create_SA()
srv_list = Service.create_services_from_json(IPv4Address("192.168.10.123"), str(Path(__file__).parent.joinpath("service_example.json").absolute()))
for srv in srv_list:
  sa.register_service(srv)


