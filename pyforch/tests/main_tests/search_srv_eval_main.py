from __future__ import annotations
import os
import sys
from typing import List

from scapy.packet import Packet
from scapy.utils import wrpcap
sys.path.append("/home/gaucho/mario/unibo_gaucho/pyforch")
# print(sys.path)
# print(sys.modules)

from src.forch.fo_service import Service
from src.forch.fo_slp import SLPFactory
from src.forch.fo_servicecache import ServiceCache
from src.forch import raise_error

from scapy.all import AsyncSniffer

from pathlib import Path
import argparse
import asyncio
from ipaddress import IPv4Address
import time # https://stackoverflow.com/questions/5849800/what-is-the-python-equivalent-of-matlabs-tic-and-toc-functions
import netifaces as ni

import csv

class TicToc:
  def __init__(self, name:str|None=None, print_out:bool=True):
    self.__name: str|None = name
    self.__tstart : float
    self.__elapsed: float = -1
    self.__print_out: bool = print_out

  def get_elapsed(self):
    return self.__elapsed

  def tic(self):
    self.__tstart = time.time()
    return self.__tstart

  def toc(self, print_out:bool|None=None):
    self.__elapsed = time.time() - self.__tstart
    if print_out is None:
      print_out = self.__print_out
    if print_out:
      if self.__name:
        print('[{}] '.format(self.__name), end='')
      print('Elapsed: {}'.format(self.__elapsed))
    return self.__elapsed

  def __enter__(self):
    self.tic()

  def __exit__(self, type, value, traceback):
    self.toc(print_out=True)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Test FORCH OpenSLP implementation.')
  # Optional arguments
  parser.add_argument('-m', '--mode', choices=['c', 'd'], default='d', help='Specify SLP working mode: c (centralized) or d (distributed).')
  parser.add_argument('-i', '--ifaces', nargs="+", help='Specify the inet ifaces where run SLP.')
  parser.add_argument('-a', '--ipaddrs', nargs="+", help='Specify the ip addresses where run SLP.')
  parser.add_argument('-j', '--files', nargs="+", default=['/home/gaucho/mario/unibo_gaucho/pyforch/tests/main_tests/srvcs_1.json'], help='Specify the service JSON files to be used.') # In a hypotetic final version, the default field should be replaced with required=True
  parser.add_argument('-t', '--times', type=int, default=1, help='Specify the number of trials to be done')
  # Mandatory arguments
  parser.add_argument('dev', choices=['o', 'n'], help='Specify the device type: o (for orchestrator) or n (for node).')
  # requiredNamed = parser.add_argument_group('required named arguments')
  # parser.add_argument('-d', '--dev', choices=['o', 'n'], required=True, help='Specify the device type: o (for orchestrator) or n (for node).')
  args = parser.parse_args()

  # This script must be run as root!
  if not os.geteuid()==0:
    sys.exit('This script must be run as root!')

  iface_list = []
  ip_list = []
  if args.ifaces is not None:
    iface_list = args.ifaces
  if args.ipaddrs is not None:
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
  for json in args.files:
    for ip in ip_list:
      srv_list.extend(Service.create_services_from_json(json_file_name=str(Path(__file__).parent.joinpath(json).absolute()), ipv4=ip))
  srv_list = Service.aggregate_nodes_of_equal_services(srv_list)

  if args.dev == 'n':
    # Sniffer not required because we sniff on the only DA/UA of the network
    sa = SLPFactory.create_SA()
    time.sleep(1)
    for srv in srv_list:
      sa.register_service(srv)
    asyncio.get_event_loop().run_forever()
  else:
    da: SLPFactory.__DirectoryAgent|None = None
    not_passed_flag: bool = False
    all_res: List[List[str]] = [['TRIAL TYPE: {}+{}'.format(args.dev, args.mode), 'TIME', 'N_PKTS', 'TOT_BYTES', 'DATA_CONSISTENCY']]

    for i in range(args.times):
      monitor: AsyncSniffer = AsyncSniffer(iface=iface_list, filter='port 427 || port 1847')
      tt: TicToc
      sc: ServiceCache
      fnd: List[Service] = []
      elapsed_time: float = -1
      pkts_list: List[Packet] = []
      n_pkts: int = -1
      tot_bytes: int = 0
      
      monitor.start()
      time.sleep(0.1)

      sc = ServiceCache()

      if args.mode == 'd':
        tt = TicToc("Test Distribuited Mode #{}".format(i))
      else:
        tt = TicToc("Test Centralized Mode #{}".format(i))

        if da is None:
          da = SLPFactory.create_DA(new_handler=True)
          input('DA started. Press enter to find services...')
        
      tt.tic()
      sc.refresh()
      elapsed_time = tt.toc()

      fnd = sc.get_list()

      time.sleep(0.1)
      pkts_list = monitor.stop()
      wrpcap(filename='./res/test{}.pcap'.format(i), pkt=pkts_list)

      n_pkts = len(pkts_list)
      for pkt in pkts_list:
        tot_bytes += len(pkt)
      print('Number of received packets: {}'.format(n_pkts))
      print('Total packets length [bytes]: {}'.format(tot_bytes))

      passed: bool = True
      for ann in srv_list:
        try:
          fnd_dict = fnd[fnd.index(ann)].__dict__
        except:
          print(1)
          input()
          passed = False
          break
        for key in ann.__dict__:
          if key != "_Service__node_list":
            try:
              if ann.__dict__[key] != fnd_dict[key]:
                print(2)
                input()
                passed = False
                break
            except:
              print(3)
              input()
              passed = False
              break
          else:
            for j, node in enumerate(ann.__dict__[key]):
              for key2 in node.__dict__:
                if key2 != "_ServiceNode__id" and key2 != "_ServiceNode__ip" and key2 != "_ServiceNode__lifetime":
                  try:
                    if node.__dict__[key2] != fnd_dict[key][j-1].__dict__[key2]:
                      print(4)
                      input()
                      passed = False
                      break
                  except:
                    print(5)
                    input()
                    passed = False
                    break
        if not passed:
          break

      if not passed and not not_passed_flag:
        not_passed_flag = True
      
      # assert passed, "Some found service is different from the registered one"
      all_res.append([str(i), str(elapsed_time), str(n_pkts), str(tot_bytes), str(passed)])

    # The file is written only at the end. This means that if the script is stopped before there will not be intermediate works available.
    # This could be an issue to be solved if needed. For the moment i prefer to access to the file once.
    with open('./res/res.csv', mode='w') as res_file:
      res_writer = csv.writer(res_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      res_writer.writerows(all_res)

    if not_passed_flag:
      raise_error("__main__", "At least one found service is not correct!")
