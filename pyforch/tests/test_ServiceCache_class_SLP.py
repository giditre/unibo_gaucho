# import sys
from pathlib import Path
# sys.path.append(str(Path(__file__).parent.parent.parent.absolute()))

from src.forch.fo_servicecache import ServiceCache
from src.forch.fo_slp import SLPFactory
from src.forch.fo_service import Service
from ipaddress import IPv4Address

def test_refresh():
  # SA MAIN
  sa = SLPFactory.create_SA()

  srv_list = Service.create_services_from_json(IPv4Address("127.0.0.1"), str(Path(__file__).parent.joinpath("service_example.json").absolute()))

  for srv in srv_list:
    sa.register_service(srv)

  #Service cache MAIN
  sc = ServiceCache()
  sc.refresh()
  fnd = sc.get_list()
  assert all([ann.__dict__ == fnd[fnd.index(ann)].__dict__ for ann in srv_list]), ""

  # Run this to catch eventual exceptions
  for srv in fnd:
    sa.deregister_service(srv)