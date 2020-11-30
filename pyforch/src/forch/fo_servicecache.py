import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

import copy

from .fo_service import Service
from .fo_slp import SLPFactory

class ServiceCache:
  def __init__(self, *, refresh=False): 
    self.__slp_ctrl = SLPFactory.create_UA()
    self.__services_list = []
    if refresh:
      self.refresh()
    
  def get_list(self, *, deepcopy=False):
    if deepcopy:
      return copy.deepcopy(self.__services_list)
    return self.__services_list
    
  def clear(self):
    self.__services_list = []
    
  def refresh(self):
    self.clear()    
    self.__services_list = self.__slp_ctrl.find_all_services()
