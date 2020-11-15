from forch.forch_utils_zabbix import ZabbixController
from forch.forch_utils_service import Service
from forch.forch_utils_service_cache import ServiceCache
from forch.forch_utils_slp import SLPController

def test_set_zabbix_controller_effectiveness():
  zc = ZabbixController()
  Service.set_zabbix_controller(zc)
  s = Service()
  assert s.get_zabbix_controller() == zc, ""

def test_service_cache_list_out():
  sc_list = ServiceCache().get_list()
  assert isinstance(sc_list, list), ""
  assert all([isinstance(service, Service) for service in sc_list]), ""

# def test_parse_json_services_file_out():
#   s_list, paths_list, lifetimes_list = Service.parse_json_services_file("tests/service_example.json")
#   assert isinstance(s_list, list), ""
#   assert all([isinstance(service, Service) for service in s_list]), ""
#   assert all([isinstance(path, str) for path in paths_list]), ""
#   assert all([isinstance(lifetime, int) for lifetime in lifetimes_list]), ""

def test_add_node_none_zc():
  pass
  # try:
  #   Service.add_node()
  # except:
  #   assert generazione_eccezione_zc

def test_retrieve_measurements_none_zc():
  #Vedi sopra ma con Service.retrieve_measurements
  pass