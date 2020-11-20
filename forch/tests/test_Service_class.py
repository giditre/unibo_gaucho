from forch.forch_utils_zabbix import ZabbixController
from forch.forch_utils_service import Service
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