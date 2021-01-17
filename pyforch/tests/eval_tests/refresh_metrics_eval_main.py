from __future__ import annotations
import os
import shutil
import sys
from typing import List

from scapy.packet import Packet
from scapy.utils import wrpcap
sys.path.append("/home/gaucho/mario/unibo_gaucho/pyforch")
# print(sys.path)
# print(sys.modules)

from src.forch.fo_service import Service, MeasurementRetrievalMode
from src.forch.fo_slp import SLPFactory
from src.forch.fo_servicecache import ServiceCache
from src.forch import set_orchestrator, raise_error

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
  parser.add_argument('-s', '--service', action="store_true", help='Use or add service refresh mode.')
  parser.add_argument('-n', '--node', action="store_true", help='Use or add node refresh mode.')
  parser.add_argument('-m', '--metric', action="store_true", help='Use or add metric refresh mode.')
  parser.add_argument('-i', '--ifaces', nargs="+", help='Specify the inet ifaces where run SLP.')
  parser.add_argument('-a', '--ipaddrs', nargs="+", help='Specify the ip addresses where run SLP.')
  parser.add_argument('-j', '--files', nargs="+", default=['/home/gaucho/mario/unibo_gaucho/pyforch/tests/eval_tests/srvcs_1.json'], help='Specify the service JSON files to be used.') # In a hypotetic final version, the default field should be replaced with required=True
  parser.add_argument('-t', '--times', type=int, default=1, help='Specify the number of trials to be done')
  args = parser.parse_args()

  # This script must be run as root!
  if not os.geteuid()==0:
    sys.exit('This script must be run as root!')

  results_path: str = './res'

  try:
    os.mkdir(results_path)
  except FileExistsError:
    try:
      shutil.rmtree(path=results_path, ignore_errors=True)
      os.mkdir(results_path)
    except:
      pass

  set_orchestrator()

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

  da = SLPFactory.create_DA(new_handler=True)
  input('DA started. Press enter to find services...')
  sc = ServiceCache(refresh=True)
  fnd = sc.get_list()

  # Check found services correctness
  # passed: bool = True
  # for ann in srv_list:
  #   try:
  #     fnd_dict = fnd[fnd.index(ann)].__dict__
  #   except:
  #     print(1)
  #     input()
  #     passed = False
  #     break
  #   for key in ann.__dict__:
  #     if key != "_Service__node_list":
  #       try:
  #         if ann.__dict__[key] != fnd_dict[key]:
  #           print(2)
  #           input()
  #           passed = False
  #           break
  #       except:
  #         print(3)
  #         input()
  #         passed = False
  #         break
  #     else:
  #       for j, node in enumerate(ann.__dict__[key]):
  #         for key2 in node.__dict__:
  #           if key2 != "_ServiceNode__id" and key2 != "_ServiceNode__ip" and key2 != "_ServiceNode__lifetime":
  #             try:
  #               if node.__dict__[key2] != fnd_dict[key][j-1].__dict__[key2]:
  #                 print(4)
  #                 input()
  #                 passed = False
  #                 break
  #             except:
  #               print(5)
  #               input()
  #               passed = False
  #               break
  #   if not passed:
  #     break

  # assert passed, "Some found service is different from the registered one!"

  mode_list: List[MeasurementRetrievalMode] = []
  if args.service:
    mode_list.append(MeasurementRetrievalMode.SERVICE)
  if args.node:
    mode_list.append(MeasurementRetrievalMode.NODE)
  if args.metric:
    mode_list.append(MeasurementRetrievalMode.METRIC)
  if not mode_list:
    mode_list = [mode for mode in MeasurementRetrievalMode]

  all_res = []
  for mode in mode_list:
    all_res.append(['MODE: {}'.format(mode.name), 'TIME', 'N_PKTS', 'TOT_BYTES'])
    for i in range(args.times):
      monitor: AsyncSniffer = AsyncSniffer(iface='lo', filter='port 80')
      tt: TicToc = TicToc(name='{} refresh test #{}'.format(mode.name, i))
      elapsed_time: float = -1
      pkts_list: List[Packet] = []
      n_pkts: int = -1
      tot_bytes: int = 0

      monitor.start()
      time.sleep(0.1)

      tt.tic()
      for srv in fnd:
        srv.refresh_measurements(mode=mode)
      elapsed_time = tt.toc()

      time.sleep(0.1)
      pkts_list = monitor.stop() # type: ignore
      wrpcap(filename='{}/{}_test{}.pcap'.format(results_path, mode.name, i), pkt=pkts_list)

      n_pkts = len(pkts_list)
      for pkt in pkts_list:
        tot_bytes += len(pkt)

      # lo double packet count compensation
      assert n_pkts % 2 == 0 and tot_bytes % 2 == 0, "Unexpected odd number!"
      n_pkts = int(n_pkts/2)
      tot_bytes = int(tot_bytes/2)

      print('Number of received packets: {}'.format(n_pkts))
      print('Total packets length [bytes]: {}'.format(tot_bytes))

      all_res.append([str(i), str(elapsed_time), str(n_pkts), str(tot_bytes)])
    all_res.append([])

  # The file is written only at the end. This means that if the script is stopped before there will not be intermediate works available.
  # This could be an issue to be solved if needed. For the moment i prefer to access to the file once.
  with open(results_path + '/res.csv', mode='w') as res_file:
    res_writer = csv.writer(res_file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    res_writer.writerows(all_res)
