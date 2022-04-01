from prometheus_client import Gauge, start_http_server
from fo_metrics import retrieve_metrics
import time

UPDATE_PERIOD = 5
SYSTEM_METRICS = {}
SYSTEM_USAGE = Gauge('system_usage', 'Hold current system resource usage', ['resource_type'])

if __name__ == '__main__':

  start_http_server(2412)

  while True:
    
    SYSTEM_METRICS = retrieve_metrics()
    
    for i in range(len(SYSTEM_METRICS['cpu'])):

      SYSTEM_USAGE.labels(f'CPU {i}').set(SYSTEM_METRICS['cpu'][f'cpu{i} usage'])
    
    for key, value in SYSTEM_METRICS['net'].items():

      SYSTEM_USAGE.labels(f'NET INT {key}').set(SYSTEM_METRICS['net'][f'{key}'])

    SYSTEM_USAGE.labels('RAM').set(SYSTEM_METRICS['ram']['available'])
    SYSTEM_USAGE.labels('DISK').set(SYSTEM_METRICS['disk']['available'])

    time.sleep(UPDATE_PERIOD)