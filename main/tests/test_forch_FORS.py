import forch

from src.main.forch_main import FORS

def test_FORS_instance():
  assert isinstance(FORS.get_instance(), FORS), ""
  FORS.del_instance()

# def test_FORS_service_list():
#   s_list = FORS.get_instance().get_service_list()
#   assert isinstance(s_list, list), ""
#   assert all( isinstance(s, forch.Service) for s in s_list ), ""

def test_FORS_service():
  s = FORS.get_instance().get_service("APP001", refresh_sc=True)
  assert isinstance(s, forch.Service), ""
  FORS.del_instance()
