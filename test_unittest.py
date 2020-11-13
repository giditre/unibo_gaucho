from forch_utils_service import Service
from forch_utils_zabbix import ZabbixController
import unittest   # The test framework

class Test_TestService(unittest.TestCase):
  def test_set_zabbix_controller(self):
    zc = ZabbixController()

    Service.set_zabbix_controller(zc)
    s = Service()

    self.assertTrue(s.get_zabbix_controller() == zc)

if __name__ == '__main__':
  unittest.main()
