from pathlib import Path
from ipaddress import IPv4Address
import docker

import forch

from src.main.fnode_main import FNVI

def test_FNVI_instance():
  assert isinstance(FNVI.get_instance(), FNVI), ""
  FNVI.del_instance()

def test_set_ipv4():
  FNVI.get_instance().set_ipv4("192.168.64.123")
  assert isinstance(FNVI.get_instance().get_ipv4(), IPv4Address), ""
  assert FNVI.get_instance().get_ipv4() == IPv4Address("192.168.64.123")
  FNVI.del_instance()

def test_load_json():
  FNVI.get_instance().set_ipv4("192.168.64.123")
  FNVI.get_instance().load_service_list_from_json(str(Path(__file__).parent.joinpath("service_example.json").absolute()))
  s_list = FNVI.get_instance().get_service_list()
  assert isinstance(s_list, list), ""
  for s in s_list:
    assert isinstance(s, forch.Service), ""
    sn_list = s.get_node_list()
    assert len(sn_list) == 1, ""
    sn = sn_list[0]
    sn_ip = sn.get_ip()
    assert isinstance(sn_ip, IPv4Address), ""
  FNVI.del_instance()

def test_docker_client():
  assert FNVI.get_instance().docker_client_test(), ""
  FNVI.del_instance()

def test_docker_image_cached():
  assert FNVI.get_instance().docker_image_is_cached("alpine:latest"), ""
  FNVI.del_instance()

def test_docker_image_not_cached():
  assert not FNVI.get_instance().docker_image_is_cached("asdasdasd"), ""
  FNVI.del_instance()

def test_docker_image_pull():
  FNVI.get_instance().docker_image_pull("giditre/gaucho-stress"), ""
  assert FNVI.get_instance().docker_image_is_cached("giditre/gaucho-stress:latest"), ""
  FNVI.del_instance()

def test_deploy_service():
  service_id = "APP001"
  image_name = "httpd"
  c = FNVI.get_instance().deploy_service_docker(service_id, image_name)
  assert c.name.startswith(service_id), str(c)
  assert isinstance(c.attrs, dict), str(c.attrs)
  assert c.attrs["Config"]["Image"] == image_name, str(c.attrs)
  FNVI.del_instance()

def test_destroy_service():
  service_id = "APP001"
  FNVI.get_instance().destroy_service_docker(service_id)
  FNVI.del_instance()

def test_destroy_all_services_individually():
  service_id_list = [ f"APP99{i}" for i in range(5) ]
  image_name = "alpine"
  for service_id in service_id_list:
    FNVI.get_instance().deploy_service_docker(service_id, image_name)
  
  for service_id in service_id_list:
    FNVI.get_instance().destroy_service_docker(service_id)
  FNVI.del_instance()

def test_destroy_all_services_together():
  service_id_list = [ f"APP99{i}" for i in range(5) ]
  image_name = "alpine"
  for service_id in service_id_list:
    FNVI.get_instance().deploy_service_docker(service_id, image_name)
  
  FNVI.get_instance().destroy_all_services_docker()
  FNVI.del_instance()

def test_list_service():
  s_id_list = FNVI.get_instance().list_containerized_services_docker()
  assert isinstance(s_id_list, list), ""
  # assert False, str(s_id_list)
  FNVI.del_instance()

def test_create_network():
  net_name = "net-test"
  FNVI.get_instance().docker_network_create_with_bridge(net_name)
  assert FNVI.get_instance().docker_network_exists(net_name), ""
  FNVI.get_instance().docker_network_prune()
  FNVI.del_instance()
