import requests
import random
import json
import argparse
from time import sleep
import logging
import os
import threading

def rand_mac():
  # 52:54:00 identifies Realtek
  return "52:54:00:%02x:%02x:%02x" % (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
            )

class FogNodeAgent(threading.Thread):

  def __init__(self, collector_address, collector_port, name="_FNA000_", log=None, lim=0, period=10):
    # TODO also consider other parameters that the init function of Thread expects (it works anyway but it's not clean)
    super().__init__()
    self.collector_address = collector_address
    self.collector_port = collector_port
    self.name = name
    self.log = log
    self.count = 0
    self.count_lim = lim
    self.period = period
    self.uuid = ""

  def run(self):

    # generate ramdom MAC address
    node_mac = rand_mac()
    node_class = random.choice(["I", "P", "S"])
    apps = [f"FA{i:03d}" for i in range(1,3)]
    sdps = [f"SDP{i:03d}" for i in range(1,4)]
    fves = [f"FVE{i:03d}" for i in range(1,4)]
    node_apps = []
    node_SDP = None
    node_FVE = None
    if node_class == "S":
      # pick no app or at most one app
      node_apps = random.sample(apps, random.randint(0,1))
    elif node_class == "P":
      # pick any number of apps
      node_apps = random.sample(apps, random.randint(0,len(apps)))
      node_SDP = random.choice(sdps)
    elif node_class == "I":
      # pick any number of apps
      node_apps = random.sample(apps, random.randint(0,len(apps)))
      node_FVE = random.choice(fves)
      
    # create informative message
    payload = {
      "mac": node_mac,
      "ipv4": "127.0.0.1",
      "class": node_class,
      "apps": node_apps,
      "SDP": node_SDP,
      "FVE": node_FVE,
      "av_res": -1
    }
    
    # wait a random amount of time before starting
    sleep(random.randint(1,5))

    while True:

      try:
        # random generation of available resource counter
        # TODO make it not random - maybe take data from Zabbix?
        payload["av_res"] = random.randint(1,100)
    
        #self.log.debug("[ {} ] {}".format(self.name, json.dumps(payload)))

        r = requests.post("http://{}:{}/nodes".format(self.collector_address, self.collector_port), json=payload)
        if self.log:
          if r.status_code == 201:
            self.name = r.json()["name"] 
            self.log.info("[ {} ] Entry created".format(self.name))
          elif r.status_code == 200:
            self.log.info("[ {} ] Entry updated".format(self.name))
          else:
            self.log.warning("[ {} ] Request failed with response code {}".format(self.name, r.status_code))

        self.count += 1
        if self.count_lim > 0 and self.count >= self.count_lim:
          break

        # wait interval before next update
        sleep(self.period)
    
      except requests.exceptions.ConnectionError as ce:
        self.log.warning("[ {} ] Connection error, retrying soon...".format(self.name))
        self.log.warning("{}".format(ce))
        # "backoff" time
        sleep(random.randint(5,15))
      except KeyboardInterrupt:
        break
  
if __name__ == "__main__":

  ### Logging setup
  
  logger = logging.getLogger(os.path.basename(__file__))
  logger.setLevel(logging.DEBUG)
  ch = logging.StreamHandler()
  ch.setLevel(logging.DEBUG)
  formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
  ch.setFormatter(formatter)
  logger.addHandler(ch)
  
  ### Command line argument parsing
  
  parser = argparse.ArgumentParser()
  
  parser.add_argument("address", help="Collector IP address")
  parser.add_argument("port", help="Collector TCP port")
  parser.add_argument("-n", "--num-agents", help="Number of FogNodeAgents to spawn", type=int, nargs="?", default=1)
  parser.add_argument("-l", "--limit-updates", help="Number of updates to send before quitting", type=int, nargs="?", default=0)
  parser.add_argument("-i", "--update-interval", help="Update interval in seconds", type=int, nargs="?", default=10)
  
  args = parser.parse_args()
  
  ep_address = args.address
  ep_port = args.port
  n_agents = args.num_agents
  lim_updates = args.limit_updates
  interval = args.update_interval
  
  for n in range(n_agents):
    fna = FogNodeAgent(ep_address, ep_port, name=f"_FNA{n:03d}_", log=logger, lim=lim_updates, period=interval)
    fna.start()

