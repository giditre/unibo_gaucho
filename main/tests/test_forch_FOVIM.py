import forch

from src.main.forch_main import FOVIM

def test_FOVIM_instance():
  assert isinstance(FOVIM.get_instance(), FOVIM), ""
  FOVIM.del_instance()

def test_manage_allocation():
  s = FOVIM.get_instance().manage_allocation(node_id="10320", service_id="APP001")
  assert isinstance(s, forch.Service), ""
  FOVIM.del_instance()

def test_manage_deployment():
  src = {
      "id": "SRC002",
      "name": "httpd",
      "descr": "Apache web server",
      "uri": "httpd",
      "base": "FVE001",      
      "service": "APP001"
    }
  s = FOVIM.get_instance().manage_deployment(service_id="APP001", node_ip="192.168.64.123", source=src)
  assert s is not None, str(s)
  assert isinstance(s, forch.Service), str(s)
  FOVIM.del_instance()