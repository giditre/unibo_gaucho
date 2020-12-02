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

def test_deploy_service():
  c = FNVI.get_instance().deploy_service("APP001", "alpine")
  # assert c.image == "alpine:latest", str(vars(c))
