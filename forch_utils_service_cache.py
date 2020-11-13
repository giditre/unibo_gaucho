class ServiceCache:
  _services_list = []

  def __init__(self, slp_controller):        
    self.__slp_ctrl = slp_controller
    self.refresh()
    
  def get_list(self):
    return self.__services_list
    
  def clear(self):
    self.__services_list = []
    
  def refresh(self):
    self.clear()    
    self.__services_list = self.__slp_ctrl.find_all_services()