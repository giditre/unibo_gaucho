"""
Produces load on all available CPU cores.
Requires system environment var STRESS_MINS to be set.
"""

from multiprocessing import Pool
from multiprocessing import cpu_count
import time
import threading
#import sys

class StressThread(threading.Thread):
  def __init__(self, duration, processes):
    super().__init__()
    self.duration = duration
    self.processes = processes

  def stress_cpu(self, duration):
    # number to use for the stress calculatio
    n = 1 + int(time.time()) % 10
    # compute when to stop
    timeout = time.time() + float(duration)  # X seconds from now
    # start stressing by computing n*n over and over
    while time.time() < timeout:
      n*n

  def run(self):
    pool = Pool(self.processes)
    for i in range(self.processes):
      pool.apply(self.stress_cpu, args = (self, self.duration, ))

if __name__ == '__main__':
  import argparse

  default_duration = 10
  default_processes = cpu_count()

  parser = argparse.ArgumentParser()  

  parser.add_argument("-t", "--duration", help="Duration of stress in seconds, default: {}".format(default_duration), type=int, nargs="?", default=default_duration)
  parser.add_argument("-n", "--processes", help="Number of parallel processes, default is cpu_count: {}".format(default_processes), type=int, nargs="?", default=default_processes)
  
  #parser.add_argument("-c", "--opt-arg-c", help="Optional boolean argument, default: False", action=store_true, default=False)

  args = parser.parse_args()

  duration = args.duration
  processes = args.processes

  print ("Stress on {} cores for {} seconds".format(processes, duration))

  t = StressThread(duration, processes)
  t.start()
  t.join()
