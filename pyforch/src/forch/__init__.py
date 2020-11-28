# Inside this module is used "sudo". Please start it with sudo permissions.
# In fo_slp there are various pylint suppressions
# Every test in *_SLP.py files in tests directory must be executed alone
# TODO M: fare classi dedicate alle eccezioni
# TODO M: vedere se mettere tutti gli enum in un unico file da importare in giro
# TODO M: rimettere thumbnail in service_example_json
# TODO M: vedere se servono davvero tutti i parametri dei vari costruttori, soprattuto per le classi in fo_service.py
# TODO M: prendere interrupt tastiera per killare slpd

# TODO G: attenzione che il campo value delle Metric è una stringa e quindi il sorting dei nodi basati su quel value potrebbe non dare il risultato desiderato

IS_ORCHESTRATOR = False

def is_orchestrator():
  global IS_ORCHESTRATOR
  return IS_ORCHESTRATOR

def set_orchestrator():
  global IS_ORCHESTRATOR
  IS_ORCHESTRATOR = True

# TODO G: forse trovare modo migliore affinchè la variabile IS_ORCHESTRATOR sia vera solo nella macchina dell'orchestratore (il problema è che teniamo tutto dentro ad un repo che sincronizziamo tra tutte le macchine, quindi non possiamo salvare un valore di IS_ORCHESTRATOR staticamente diverso per ogni macchina). Proposta: fare un file di config (fuori dal repo) da leggere all'avvio

from .fo_tools import get_lst, raise_error
from .fo_service import Service
from .fo_servicecache import ServiceCache
from .fo_slp import SLPFactory
from .fo_zabbix import ZabbixAPI, ZabbixAdapter, ZabbixNode, ZabbixNodeFields

# __all__ = ()