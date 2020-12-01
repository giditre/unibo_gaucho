import forch

from src.main.forch_main import FOB

def test_FOB_instance():
  assert isinstance(FOB.get_instance(), FOB), ""

def test_FOB_service_list():
  s_list = FOB.get_instance().get_service_list()
  assert isinstance(s_list, list), ""
  assert all( isinstance(s, forch.Service) for s in s_list ), ""

def test_FOB_service_list_refresh_cache():
  s_list = FOB.get_instance().get_service_list(refresh_sc=True)
  assert isinstance(s_list, list), ""
  assert len(s_list) > 0, ""
  assert all( isinstance(s, forch.Service) for s in s_list ), ""

def test_FOB_service_list_refresh_all():
  s_list = FOB.get_instance().get_service_list(refresh_sc=True, refresh_meas=True)
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
      # for m_type in forch.MetricType:


def test_FOB_allocate_service():
  s = FOB.get_instance().allocate_service("APP001")
  assert isinstance(s, forch.Service), ""
