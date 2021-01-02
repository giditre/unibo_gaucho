import logging
from typing import List

from .fo_service import Service

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

import copy

from .fo_slp import SLPFactory


class ServiceCache:
  def __init__(self, *, refresh:bool=False): 
    self.__slp_ctrl: SLPFactory.__UserAgent = SLPFactory.create_UA()
    self.__service_list: List[Service] = []
    if refresh:
      self.refresh()
    
  def get_list(self, *, deepcopy:bool=False) -> List[Service]:
    if deepcopy:
      return copy.deepcopy(self.__service_list)
    return self.__service_list
    
  def clear(self):
    self.__service_list = []
    
  def refresh(self):
    self.clear()    
    self.__service_list = self.__slp_ctrl.find_all_services()
