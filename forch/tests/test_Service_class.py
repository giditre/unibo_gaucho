from src.forch_utils_zabbix import ZabbixController
from src.forch_utils_service import Service
from ipaddress import IPv4Address

def test_create_services_from_json_out_in():
  # Service.create_services_from_json("127.0.0.1", "tests/service_example.json")
  # TODO M: raisare l'eccezione IPv4
  # TODO M: raisare che il file non esiste
  pass

def test_create_services_from_json_out():
  s_list = Service.create_services_from_json(IPv4Address("127.0.0.1"), "tests/service_example.json")
  assert isinstance(s_list, list), ""
  assert all([isinstance(service, Service) for service in s_list]), ""
  assert all([service.get_node_list() for service in s_list]), ""

# def test_pickle_single():
#   s_in = Service(id="APP000")
#   p = s_in.to_pickle()
#   s_out = Service.from_pickle(p)
#   assert isinstance(s_out, Service)
#   assert s_in == s_out

# def test_pickle_list():
#   s_list = Service.create_services_from_json(IPv4Address("127.0.0.1"), "tests/service_example.json")
#   p_list = [ s_in.to_pickle() for s_in in s_list ]
#   for i, p in enumerate(p_list):
#     s_out = Service.from_pickle(p)
#     assert isinstance(s_out, Service)
#     assert s_list[i] == s_out

#TODO M: fare i seguenti test

def test_add_node_none_zc():
  pass
  # try:
  #   Service.add_node()
  # except:
  #   assert generazione_eccezione_zc

def test_retrieve_measurements_none_zc():
  #Vedi commenti sopra ma con Service.retrieve_measurements
  pass

def test_metric_json():
  # TODO G: verificare che si riesca a creare un oggetto Metric a partire da un JSON che lo rappresenta. Fare lo stesso per ServiceNode e Service
  pass