import logging
from logging.config import fileConfig
from pathlib import Path
fileConfig(str(Path(__file__).parent.joinpath("logging.ini")))
logger = logging.getLogger(__name__)
logger.info(f"Load {__name__} with {logger}")

import forch

logger.debug("IS_ORCHESTRATOR: {}".format(forch.is_orchestrator()))

from ipaddress import IPv4Address
import asyncio
import time

sa = forch.SLPFactory.create_SA()

if forch.is_orchestrator():
  srv_list = forch.Service.create_services_from_json(IPv4Address("127.0.0.1"), str(Path(__file__).parent.joinpath("service_example.json").absolute()))
else:
  # TODO G: prendere indirizzo IP da interfaccia usata sulla rete fog
  srv_list = forch.Service.create_services_from_json(IPv4Address("192.168.64.123"), str(Path(__file__).parent.joinpath("service_example.json").absolute()))

for srv in srv_list:
  print(srv)
  sa.register_service(srv)

asyncio.get_event_loop().run_forever()
