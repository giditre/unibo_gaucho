import sys
print(sys.path)
print(sys.modules)

from src.forch.fo_service import Service
from src.forch.fo_slp import SLPFactory
from src.forch.fo_servicecache import ServiceCache

# import pyshark

from pathlib import Path
import argparse
import asyncio
from ipaddress import IPv4Address
import netifaces as ni

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Test FORCH OpenSLP implementation.')
  parser.add_argument('--dev', metavar='device', choices=['o', 'n'], required=True, help='Specify the device type: o (for orchestrator) or n (for node).')
  parser.add_argument('--mode', metavar='mode', choices=['c', 'd'], default='d', help='Specify SLP working mode: c (centralized) or d (distributed).')
  parser.add_argument('--ifaces', nargs="+", help='Specify the inet ifaces where run SLP.')
  parser.add_argument('--ipaddrs', nargs="+", help='Specify the ip addresses where run SLP.')
  parser.add_argument('--files', nargs="+", help='Specify the service JSON files to be used.')
  args = parser.parse_args()

  if 'args.files' in locals():
    json_list = [str(Path(__file__).parent.joinpath(file).absolute()) for file in args.files]
  else:
    json_list = [str(Path(__file__).parent.joinpath("../service_example.json").absolute())]


  iface_list = []
  ip_list = []
  if 'args.ifaces' in locals():
    iface_list = args.ifaces
  if 'args.ipaddrs' in locals():
    ip_list = [IPv4Address(ip) for ip in args.ipaddrs]
  if not iface_list and not ip_list:
    iface_list = ni.interfaces()

  #ipv4 = ni.ifaddresses('lo')[ni.AF_INET][0]['addr']
  for iface in iface_list:
   for ip in ni.ifaddresses(str(iface))[ni.AF_INET]:
     ip_list.append(ip['addr'])

  ip_list = list(set(ip_list))

  # parse json files
  srv_list = []
  for json in json_list:
    for ip in ip_list:
      srv_list.append(Service.create_services_from_json(json_file_name=json, ipv4=ip))
  srv_list = Service.aggregate_nodes_of_equal_services(srv_list)

  if args.dev == 'n':
    sa = SLPFactory.create_SA()
    for srv in srv_list:
      sa.register_service(srv)
    asyncio.get_running_loop().run_forever()
  else:
    if args.mode == 'c':
      sc = ServiceCache()
      #tic
      sc.refresh()
      #toc
      fnd = sc.get_list()
    else:
      da = SLPFactory.create_DA()
      ua = SLPFactory.create_UA()
      #tic
      fnd = ua.find_all_services()
      #toc

    assert all([ann.__dict__ == fnd[fnd.index(ann)].__dict__ for ann in srv_list]), "Some found service is different from the registered one"
    pass
