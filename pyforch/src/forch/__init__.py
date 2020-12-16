# Inside this module is used "sudo". Please start it with sudo permissions.
# In fo_slp there are various pylint suppressions
# Every test in *_SLP.py files in tests directory must be executed alone
# TODO M: fare classi dedicate alle eccezioni
# TODO M: vedere se mettere tutti gli enum in un unico file da importare in giro
# TODO M: rimettere thumbnail in service_example_json
# TODO M: vedere se servono davvero tutti i parametri dei vari costruttori, soprattuto per le classi in fo_service.py
# TODO M: prendere interrupt tastiera per killare slpd

# TODO G: attenzione che il campo value delle Metric è una stringa e quindi il sorting dei nodi basati su quel value potrebbe non dare il risultato desiderato

_is_orchestrator = False

def is_orchestrator():
  global _is_orchestrator
  return _is_orchestrator

def set_orchestrator():
  global _is_orchestrator
  _is_orchestrator = True

def get_lst(item):
  if item is None:
    return item
  return [item] if not isinstance(item, list) else item

def raise_error(class_name, msg=""):
  try:
    raise NameError(class_name)
  except NameError:
    print(msg)
    raise
  