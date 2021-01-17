# Inside this module is used "sudo". Please start it with sudo permissions.
# In fo_slp there are various pylint suppressions
# Every test in *_SLP.py files in tests directory must be executed alone
# TODO: create exception classes
# TODO: Improvement: Right now SLP urls are supposed to contains node IPs only. SLP can be used also alongside DNS, hence allows literal URLs.
#       For shake of generality add this possibility adding a field in ServiceNode class. Of course this requires a little bit of code revision
#       because also the related methods must support this new field.
# TODO BUG: Python doesn't allow to execute supbrocess.run() inside __del__ stack when the Python script is ending. It says that cannot start new
#           processes because Python is shutting down or something similar. This means that slpd cannot be stopped and remains alive when the Python
#           script ends. This is a quite critical issue that must be solved.
#           Maybe a possible solution would be to use "-d" slpd option which don't detach the daemon by the invocator process.

# TODO G: Pay attention: Metric field value is a string, hence the node sorting based on that value could return unexpected results

# This import allows to hint custom classes and to use | instead of Union[]
# TODO: remove it when Python 3.10 will be used
from __future__ import annotations
from typing import Any, List, NoReturn


_is_orchestrator = False

def is_orchestrator():
  global _is_orchestrator
  return _is_orchestrator

def set_orchestrator():
  global _is_orchestrator
  _is_orchestrator = True

def get_lst(item:Any) -> List[Any]|None:
  if item is None:
    return item
  return [item] if not isinstance(item, list) else item

def raise_error(class_name:str, msg:str="") -> NoReturn:
  try:
    raise NameError(class_name)
  except NameError:
    print(msg)
    raise
  