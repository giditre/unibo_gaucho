import forch

from src.main.forch_main import FOA

def test_FORS_instance():
  assert isinstance(FOA.get_instance(), FOA), ""
  FOA.del_instance()

# def test_FORS_service_list():
#   s_list = FORS.get_instance().get_service_list()
#   assert isinstance(s_list, list), ""
#   assert all( isinstance(s, forch.Service) for s in s_list ), ""

def test_FORS_service():
  s = FOA.get_instance().get_service("APP001", refresh_sc=True)
  assert isinstance(s, forch.Service), ""
  FOA.del_instance()
