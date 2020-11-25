import copy

from .forch_utils_service import Service
from .forch_utils_slp import SLPFactory

class ServiceCache:
  def __init__(self): 
    self.__slp_ctrl = SLPFactory.create_UA()
    self.__services_list = []
    # self.refresh() # TODO M: decidere se farlo, secondo me meglio di no. Uno si instanzia una cache poi sa che deve refresharla quando vuole lui
    
  def get_list(self):
    return copy.deepcopy(self.__services_list)
    
  def clear(self):
    self.__services_list = []
    
  def refresh(self):
    self.clear()    
    self.__services_list = self.__slp_ctrl.find_all_services()