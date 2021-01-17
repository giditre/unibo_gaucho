import logging
from typing import List

from .fo_service import Service

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

import copy

from .fo_slp import SLPFactory


class ServiceCache:
  def __init__(self, *, refresh:bool=False):
    """ServiceCache contructor method.

    Args:
        refresh (bool, optional): specifies if the constructor must automatically populate the cache. Defaults to False.
    """
    self.__slp_ctrl: SLPFactory.__UserAgent = SLPFactory.create_UA()
    self.__service_list: List[Service] = []
    if refresh:
      self.refresh()
    
  def get_list(self, *, deepcopy:bool=False) -> List[Service]:
    """This method returns the intertnal list with the cached services.

    Args:
        deepcopy (bool, optional): Specifies if the method must returns the actual lits or its copy. Defaults to False.

    Returns:
        List[Service]: cached services list.
    """
    if deepcopy:
      return copy.deepcopy(self.__service_list)
    return self.__service_list
    
  def clear(self):
    """
        This method empty the internal cache list.
    """
    self.__service_list = []
    
  def refresh(self):
    """
        This method refresh the cache in order to update the known services.
    """
    self.clear()    
    self.__service_list = self.__slp_ctrl.find_all_services()
