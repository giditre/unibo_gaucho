import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from forch.forch_utils_service_cache import ServiceCache # pylint: disable=import-error
from forch.forch_utils_slp import SLPFactory # pylint: disable=import-error
from forch.forch_utils_service import Service # pylint: disable=import-error
from ipaddress import IPv4Address
import asyncio

import json

# da = SLPFactory.create_DA()

#Service cache MAIN
sc = ServiceCache()
sc.refresh()
fnd = sc.get_list()

for s in fnd:
  print(json.dumps(s, default=lambda x: x.to_json()))

asyncio.get_event_loop().run_forever()