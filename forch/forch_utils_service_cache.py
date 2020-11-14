import copy

from forch.forch_utils_service import Service
from forch.forch_utils_slp import SLPController, SLPAgentType

class ServiceCache:
  def __init__(self):        
    self.__slp_ctrl = SLPController(SLPAgentType.UA)
    self.__services_list = []
    self.refresh()
    
  def get_list(self):
    return copy.deepcopy(self.__services_list)
    
  def clear(self):
    self.__services_list = []
    
  def refresh(self):
    self.clear()    
    self.__services_list = self.__slp_ctrl.find_all_services()