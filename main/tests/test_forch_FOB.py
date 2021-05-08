import forch

from src.main.forch_main import FOM

def test_FOB_instance():
  assert isinstance(FOM.get_instance(), FOM), ""
  FOM.del_instance()

def test_FOB_service_list():
  s_list = FOM.get_instance().get_service_list()
  assert isinstance(s_list, list), ""
  assert all( isinstance(s, forch.Service) for s in s_list ), ""
  FOM.del_instance()

def test_FOB_service_list_refresh_cache():
  s_list = FOM.get_instance().get_service_list(refresh_sc=True)
  assert isinstance(s_list, list), ""
  assert len(s_list) > 0, ""
  assert all( isinstance(s, forch.Service) for s in s_list ), ""
  FOM.del_instance()

def test_FOB_service_list_refresh_all():
  s_list = FOM.get_instance().get_service_list(refresh_sc=True, refresh_meas=True)
  assert isinstance(s_list, list), ""
  assert len(s_list) > 0, ""
  assert all( isinstance(s, forch.Service) for s in s_list ), ""
  for s in s_list:
    sn_list = s.get_node_list()
    assert isinstance(sn_list, list), ""
    assert len(sn_list) > 0, ""
    # assert all( isinstance(s, forch.Service.__ServiceNode) for sn in sn_list ), ""
    for sn in sn_list:
      m_list = sn.get_metrics_list()
      assert isinstance(m_list, list), ""
      assert len(m_list) > 0, ""
      # assert all( isinstance(s, forch.Service.__ServiceNode.__Metric) for m in m_list ), ""
      for m_type in forch.MetricType:
        assert sn.get_metric_by_type(m_type) is not None, ""
  FOM.del_instance()

def test_FOB_activate_service_200():
  s = FOM.get_instance().activate_service("APP001")
  assert isinstance(s, forch.Service), ""
  # assert c == 200, ""
  FOM.del_instance()

def test_FOB_activate_service_201():
  s = FOM.get_instance().activate_service("APP003")
  assert isinstance(s, forch.Service), ""
  # assert c == 201, ""
  FOM.del_instance()

def test_FOB_activate_service_404():
  s = FOM.get_instance().activate_service("APP000")
  assert s is None, ""
  # assert c == 404, ""
  FOM.del_instance()
