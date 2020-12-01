from src.forch.fo_zabbix import ZabbixAdapter
from src.forch.fo_service import Service, MetricType
from src.forch import set_orchestrator, is_orchestrator

set_orchestrator()

from ipaddress import IPv4Address

def test_create_services_from_json_out_in():
  # Service.create_services_from_json("127.0.0.1", "tests/service_example.json")
  # TODO M: raisare l'eccezione IPv4
  # TODO M: raisare che il file non esiste
  pass

def test_create_services_from_json_out():
  s_list = Service.create_services_from_json(IPv4Address("127.0.0.1"), "tests/service_example.json")
  assert isinstance(s_list, list), ""
  assert all([isinstance(s, Service) for s in s_list]), ""
  assert all([s.get_node_list() for s in s_list]), ""

def test_create_single_service():
  s = Service(id="APP001")
  assert isinstance(s, Service), ""
  assert s.get_id() == "APP001", ""
  assert is_orchestrator(), ""
  s.add_node(ipv4="192.168.64.123")
  node_list = s.get_node_list()
  assert isinstance(node_list, list), ""
  assert len(node_list) == 1, ""
  sn = node_list[0]
  # assert sn.get_id() == "192.168.64.123"
  assert sn.get_ip() == IPv4Address("192.168.64.123")

def test_refresh_measurements():
  s = Service(id="APP001")
  s.add_node(ipv4="192.168.64.123")
  s.refresh_measurements()
  node_list = s.get_node_list()
  sn = node_list[0]
  metrics_list = sn.get_metrics_list()
  assert isinstance(metrics_list, list), ""
  assert len(metrics_list) == len(MetricType), ""
  # assert False, str(s)

# def test_metric_json():
#   # TODO G: verificare che si riesca a creare un oggetto Metric a partire da un JSON che lo rappresenta. Fare lo stesso per ServiceNode e Service
#   pass