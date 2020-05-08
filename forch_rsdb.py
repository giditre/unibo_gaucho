from flask import Flask, request, jsonify
from flask_restful import Resource, Api, reqparse, abort
import json
import argparse
from time import time, sleep
import uuid
import logging
import os
import threading
from copy import deepcopy
import requests
import random

import threading
from multiprocessing import Process

from pyzabbix import ZabbixAPI

### Logging setup

from logging.config import dictConfig as logging_dictConfig
logging_dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[ %(asctime)s ][ {:<21} ][ %(levelname)s ] %(message)s'.format(os.path.basename(__file__)),
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
#ch = logging.StreamHandler()
#ch.setLevel(logging.DEBUG)
#formatter = logging.Formatter('[ %(asctime)s ][ %(filename)s ][ %(levelname)s ] %(message)s')
#ch.setFormatter(formatter)
#logger.addHandler(ch)

### Command line argument parser

parser = argparse.ArgumentParser()

parser.add_argument("address", help="Endpoint IP address")
parser.add_argument("port", type=int, help="Endpoint TCP port")
parser.add_argument("--db-json", help="Database JSON file, default: rsdb.json", nargs="?", default="rsdb.json")
parser.add_argument("--imgmt-address", help="IaaS management endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
parser.add_argument("--imgmt-port", help="IaaS management endpoint TCP port, default: 5004", type=int, nargs="?", default=5004)
parser.add_argument("-w", "--wait-remote", help="Wait for remote endpoint(s), default: false", action="store_true", default=False)
parser.add_argument("--mon-history", help="Number of monitoring elements to keep in memory, default: 300", type=int, nargs="?", default=300)
parser.add_argument("--mon-period", help="Monitoring period in seconds, default: 10", type=int, nargs="?", default=10)
parser.add_argument("-d", "--debug", help="Run in debug mode, default: false", action="store_true", default=False)

args = parser.parse_args()

ep_address = args.address
ep_port = args.port
db_fname = args.db_json
iaas_mgmt_address = args.imgmt_address
iaas_mgmt_port = args.imgmt_port
wait_remote = args.wait_remote
monitor_history = args.mon_history
monitor_period = args.mon_period
debug = args.debug

### Zabbix

class Zabbix():

  def __init__(self, url='http://localhost/zabbix/', user='Admin', password='zabbix'):
    self.zapi = ZabbixAPI(url=url, user=user, password=password)
    
  def get_nodes(self, server_name = "Zabbix Server"):
    fields = ["hostid", "name", "status", "available"]
    nodes = { h["hostid"]: { f: h[f] for f in fields } for h in self.zapi.host.get(search={"name": server_name}, excludeSearch=True) }
    interfaces = self.zapi.hostinterface.get()
    for i in interfaces:
      hostid = i["hostid"]
      if hostid in nodes:
        nodes[hostid]["ip"] = i["ip"]
    return nodes

  #def get_node(self, node_id):
  #  hosts = self.zapi.host.get(filter={"hostid": node_id})
  #  if hosts:
  #    return hosts[0]
  #  else:
  #    return {"message": "Node {} not found.".format(node_id)}

  def get_measurements(self, node_id=None, search_str=""):
    fields = [ "hostid", "itemid", "name", "lastclock", "lastvalue", "units" ]
    measurements = [ { f: item[f] for f in fields } for item in self.zapi.item.get(filter={"hostid": node_id}, search={"name": "*{}*".format(search_str)}, searchWildcardsEnabled=True) ]
    #logger.debug("MEASUREMENTS", measurements)
    return measurements

### user functions

def mac_to_uuid(mac):
  # generate deterministic UUID based on MAC address of node
  return str(uuid.uuid3(uuid.NAMESPACE_DNS, mac))

def write_db_to_file(fname, db_json, period=0):
  with open(fname, "w") as f:
    json.dump(db_json, f)
  if period:
    threading.Timer(period, write_db_to_file, args=[fname, db_json, period]).start()

def wait_for_remote_endpoint(ep_address, ep_port, path="test"):
  url = "http://{}:{}/{}".format(ep_address, ep_port, path)
  while True:
    resp_code = -1
    try:
      r = requests.get(url)
      resp_code = r.status_code
    except requests.exceptions.ConnectionError as ce:
      logger.warning("Connection error, retrying soon...")
    if resp_code == 200:
      logger.info("Remote endpoint ({}) ready".format(url))
      break
    logger.warning("Remote endpoint ({}) not ready (reponse code {}), retrying soon...".format(url, resp_code))
    sleep(random.randint(5,15))
    
### discovery and monitoring

class RSDM(threading.Thread):
  """Resource and Service Discovery and Monitoring"""
  
  def __init__(self):
    super().__init__()
    self.rsdm_dict = {}
    self.collector = Zabbix()
    self.monitoring_interval = monitor_period
    self.max_history = monitor_history
    self.dict_lock = threading.Lock()
    self.monitor = threading.Event()

  def do_monitor(self):

    #logger.debug("Monitor is collecting measurements")

    # TODO check for new hosts - or this in implicit in the length of the monitor list?
    # monitor utilization of resources
    t = round(time())
    with self.dict_lock:
      self.rsdm_dict[t] = {}
      for node_id in self.collector.get_nodes():
        self.rsdm_dict[t][node_id] = {}
        for item in self.collector.get_measurements(node_id=node_id, search_str="utilization"):
          #lastclock = int(item["lastclock"])
          #if lastclock == 0:
          #  continue
          self.rsdm_dict[t][node_id][item["itemid"]] = item
      # keep maximum size of dictionary limited to max_history values
      if len(self.rsdm_dict) > self.max_history:
        oldest_t = min(self.rsdm_dict.keys())
        del self.rsdm_dict[oldest_t]

    #logger.debug("DICT", self.rsdm_dict)

  def run(self):
    self.monitor.set()
    while self.monitor.is_set():
      curr_time = time()
      next_time = curr_time - (curr_time%1.0) + self.monitoring_interval

      self.do_monitor()

      sec_to_next_time = next_time - time()
      sleep(next_time - time())

  def start_monitoring(self):
    self.start()

  def stop_monitoring(self):
    self.monitor.clear()

  def get_all_measurements(self):
    return self.rsdm_dict

  def get_last_measurements(self, node_id):
    newest_t = max(self.rsdm_dict.keys())
    #logger.debug("RESOURCES", self.rsdm_dict[newest_t][node_id])
    return self.rsdm_dict[newest_t][node_id]

### manage database

class RSDB():

  """ Resourcs and Services Database """

  def __init__(self):
    # initialize nodes and apps databases as empty dicts
    self.rsdb = self.init_db()
    self.db_lock = threading.Lock()
  
    # write initial database
    #write_db_to_file(db_fname, self.rsdb, period=10)

    self.write_db = True

    self.collector = Zabbix()

    self.rsdm = RSDM()
    self.rsdm.start()

  def init_db(self):
    rsdb = { "nodes": {} }

    # load apps from file and populate catalog
    with open("db_apps.json") as f:
      app_cat = json.load(f)
    with open("db_sdps.json") as f:
      sdp_cat = json.load(f)
    with open("db_fves.json") as f:
      fve_cat = json.load(f)

    rsdb["app_catalog"] = app_cat["apps"]
    rsdb["sdp_catalog"] = sdp_cat["sdps"]
    rsdb["fve_catalog"] = fve_cat["fves"]

    rsdb["apps"] = deepcopy(rsdb["app_catalog"])
    for app in rsdb["app_catalog"]:
      rsdb["apps"][app]["nodes"] = []

    rsdb["sdps"] = deepcopy(rsdb["sdp_catalog"])
    for sdp in rsdb["sdp_catalog"]:
      rsdb["sdps"][sdp]["nodes"] = []

    rsdb["fves"] = deepcopy(rsdb["fve_catalog"])
    for fve in rsdb["fve_catalog"]:
      rsdb["fves"][fve]["nodes"] = []    

    return rsdb   

  def get_node_fields(self):
    return self.node_fields

  def get_node_list(self):
    with self.db_lock:
      self.rsdb["nodes"] = self.collector.get_nodes()
      # maybe avoid asking nodes directly, but go through forch_iaas_mgmt? - but then what about non-IaaS nodes?

      for node_id in self.rsdb["nodes"]:

        self.rsdb["nodes"][node_id]["apps"] = []
        self.rsdb["nodes"][node_id]["sdps"] = []
        self.rsdb["nodes"][node_id]["fves"] = []

        try:
          node_info = requests.get("http://{}:5005/info".format(self.rsdb["nodes"][node_id]["ip"])).json()
        except requests.exceptions.ConnectionError:
          self.rsdb["nodes"][node_id]["class"] = ""
          self.rsdb["nodes"][node_id]["available"] = "0"
          continue

        if node_info["class"] == "S":
          self.rsdb["nodes"][node_id]["class"] = node_info["class"]
          try:
            node_apps = requests.get("http://{}:5005/apps".format(self.rsdb["nodes"][node_id]["ip"])).json()
          except requests.exceptions.ConnectionError:
            # TODO signal the error
            logger.debug("Error in connecting to http://{}:5005/apps".format(self.rsdb["nodes"][node_id]["ip"]))
            continue
          for app_id in node_apps["apps"]:
            self.rsdb["nodes"][node_id]["apps"].append(app_id)
          # get monitoring information
          self.rsdb["nodes"][node_id]["resources"] = self.rsdm.get_last_measurements(node_id)
          # update apps database
          for app in self.rsdb["nodes"][node_id]["apps"]:
            if app in self.rsdb["apps"]:
              if node_id not in self.rsdb["apps"][app]["nodes"]:
                self.rsdb["apps"][app]["nodes"].append(node_id)
            else:
              # get app structure from catalog
              self.rsdb["apps"][app] = deepcopy(self.rsdb["app_catalog"][app])
              self.rsdb["apps"][app]["nodes"] = [node_id]
          # remove node from app db if it does no longer offer that app
          for app in self.rsdb["apps"]:
            if app not in self.rsdb["nodes"][node_id]["apps"] and node_id in self.rsdb["apps"][app]["nodes"]:
              self.rsdb["apps"][app]["nodes"].remove(node_id)

        elif node_info["class"] == "P":
          self.rsdb["nodes"][node_id]["class"] = node_info["class"]
          try:
            node_sdps = requests.get("http://{}:5005/sdps".format(self.rsdb["nodes"][node_id]["ip"])).json()
          except requests.exceptions.ConnectionError:
            # TODO signal the error
            logger.debug("Error in connecting to http://{}:5005/sdps".format(self.rsdb["nodes"][node_id]["ip"]))
            continue
          for sdp_id in node_sdps["sdps"]:
            self.rsdb["nodes"][node_id]["sdps"].append(sdp_id)
          # get monitoring information 
          self.rsdb["nodes"][node_id]["resources"] = self.rsdm.get_last_measurements(node_id)
          # update sdps database
          for sdp in self.rsdb["nodes"][node_id]["sdps"]:
            if sdp in self.rsdb["sdps"]:
              if node_id not in self.rsdb["sdps"][sdp]["nodes"]:
                self.rsdb["sdps"][sdp]["nodes"].append(node_id)
            else:
              # get sdp structure from catalog
              self.rsdb["sdps"][sdp] = deepcopy(self.rsdb["sdp_catalog"][sdp])
              self.rsdb["sdps"][sdp]["nodes"] = [node_id]
          # remove node from sdp db if it does no longer offer that sdp
          for sdp in self.rsdb["sdps"]:
            if sdp not in self.rsdb["nodes"][node_id]["sdps"] and node_id in self.rsdb["sdps"][sdp]["nodes"]:
              self.rsdb["sdps"][sdp]["nodes"].remove(node_id)
      
        elif node_info["class"] == "I":
          self.rsdb["nodes"][node_id]["class"] = node_info["class"]
          try:
            node_apps = requests.get("http://{}:5005/apps".format(self.rsdb["nodes"][node_id]["ip"])).json()
            node_sdps = requests.get("http://{}:5005/sdps".format(self.rsdb["nodes"][node_id]["ip"])).json()
            node_fves = requests.get("http://{}:5005/fves".format(self.rsdb["nodes"][node_id]["ip"])).json()
          except requests.exceptions.ConnectionError:
            # TODO signal the error
            logger.debug("Error in connecting to {}".format(self.rsdb["nodes"][node_id]["ip"]))
            continue

          # APPs
          for app_id in node_apps["apps"]:
            self.rsdb["nodes"][node_id]["apps"].append(app_id)
          # get monitoring information
          self.rsdb["nodes"][node_id]["resources"] = self.rsdm.get_last_measurements(node_id)
          # update apps database
          for app in self.rsdb["nodes"][node_id]["apps"]:
            if app in self.rsdb["apps"]:
              if node_id not in self.rsdb["apps"][app]["nodes"]:
                self.rsdb["apps"][app]["nodes"].append(node_id)
            else:
              # get app structure from catalog
              self.rsdb["apps"][app] = deepcopy(self.rsdb["app_catalog"][app])
              self.rsdb["apps"][app]["nodes"] = [node_id]
          # remove node from app db if it does no longer offer that app
          for app in self.rsdb["apps"]:
            if app not in self.rsdb["nodes"][node_id]["apps"] and node_id in self.rsdb["apps"][app]["nodes"]:
              self.rsdb["apps"][app]["nodes"].remove(node_id)

          # SDPs
          for sdp_id in node_sdps["sdps"]:
            self.rsdb["nodes"][node_id]["sdps"].append(sdp_id)
          # get monitoring information 
          self.rsdb["nodes"][node_id]["resources"] = self.rsdm.get_last_measurements(node_id)
          # update sdps database
          for sdp in self.rsdb["nodes"][node_id]["sdps"]:
            if sdp in self.rsdb["sdps"]:
              if node_id not in self.rsdb["sdps"][sdp]["nodes"]:
                self.rsdb["sdps"][sdp]["nodes"].append(node_id)
            else:
              # get sdp structure from catalog
              self.rsdb["sdps"][sdp] = deepcopy(self.rsdb["sdp_catalog"][sdp])
              self.rsdb["sdps"][sdp]["nodes"] = [node_id]
          # remove node from sdp db if it does no longer offer that sdp
          for sdp in self.rsdb["sdps"]:
            if sdp not in self.rsdb["nodes"][node_id]["sdps"] and node_id in self.rsdb["sdps"][sdp]["nodes"]:
              self.rsdb["sdps"][sdp]["nodes"].remove(node_id)

          # FVEs
          for fve_id in node_fves["fves"]:
            self.rsdb["nodes"][node_id]["fves"].append(fve_id)
          # get monitoring information
          self.rsdb["nodes"][node_id]["resources"] = self.rsdm.get_last_measurements(node_id)
          # update fves database
          for fve in self.rsdb["nodes"][node_id]["fves"]:
            if fve in self.rsdb["fves"]:
              if node_id not in self.rsdb["fves"][fve]["nodes"]:
                self.rsdb["fves"][fve]["nodes"].append(node_id)
            else:
              # get fve structure from catalog
              self.rsdb["fves"][fve] = deepcopy(self.rsdb["fve_catalog"][fve])
              self.rsdb["fves"][fve]["nodes"] = [node_id]
          # remove node from fve db if it does no longer offer that fve
          for fve in self.rsdb["fves"]:
            if fve not in self.rsdb["nodes"][node_id]["fves"] and node_id in self.rsdb["fves"][fve]["nodes"]:
              self.rsdb["fves"][fve]["nodes"].remove(node_id)

        else:
          # TODO handle error
          logger.debug("Unhandled class {}".format(node_info["class"]))

    return self.rsdb["nodes"]

  def get_node(self, node_id):
    if node_id in self.rsdb["nodes"]:
      return self.rsdb["nodes"][node_id], 200
    else:
      return {
        "message": "Node {} not in database, update database by performing GET /nodes and try again".format(node_id),
      }, 404

  def get_measurements(self):
    return self.rsdm.get_all_measurements()

  def get_app_catalog(self):
    return self.rsdb["app_catalog"]

  def get_app_list(self):
    return self.rsdb["apps"]

  def get_app(self, app_id):
    if app_id not in self.rsdb["apps"]:
      return {
        "message": "APP {} not found.".format(app_id)
      }, 404
    return self.rsdb["apps"][app_id]

  def get_sdp_catalog(self):
    return self.rsdb["sdp_catalog"]

  def get_sdp_list(self):
    return self.rsdb["sdps"]

  def get_sdp(self, sdp_id):
    if sdp_id not in self.rsdb["sdps"]:
      return {
        "message": "SDP {} not found.".format(app_id)
      }, 404
    return self.rsdb["sdps"][sdp_id]

  def get_fve_catalog(self):
    return self.rsdb["fve_catalog"]

  def get_fve_list(self):
    return self.rsdb["fves"]

  def get_fve(self, fve_id):
    if fve_id not in self.rsdb["fves"]:
      return {
        "message": "FVE {} not found.".format(app_id)
      }, 404
    return self.rsdb["fves"][fve_id]

  def flush_db(self):
    with self.db_lock:
      self.rsdb = self.init_db()
    return {
      "message": "Database re-initialized"}, 200

  def delete_apps_node(self, node_id):
    node_ip = self.rsdb["nodes"][node_id]["ip"]
    try:
      r = requests.delete("http://{}:5005/apps".format(node_ip))
    except requests.exceptions.ConnectionError as e:
      # handle error
      #logger.debug(str(e))
      logger.info("Node {} at {} not available for DELETE".format(node_id, node_ip))

  def delete_apps(self):
    process_list = []
    for node_id in self.rsdb["nodes"]:
      if self.rsdb["nodes"][node_id]["apps"]:
        p = Process(target=self.delete_apps_node, args=(node_id,))
        p.start()
        process_list.append(p)
    for p in process_list:
      p.join()
    return {"message": "APPs deleted on all nodes."}, 200

  def delete_sdps_node(self, node_id):
    node_ip = self.rsdb["nodes"][node_id]["ip"]
    try:
      r = requests.delete("http://{}:5005/sdps".format(node_ip))
    except requests.exceptions.ConnectionError as e:
      # handle error
      #logger.debug(str(e))
      logger.info("Node {} at {} not available for DELETE".format(node_id, node_ip))

  def delete_sdps(self):
    process_list = []
    for node_id in self.rsdb["nodes"]:
      if self.rsdb["nodes"][node_id]["sdps"]:
        p = Process(target=self.delete_sdps_node, args=(node_id,))
        p.start()
        process_list.append(p)
    for p in process_list:
      p.join()
    return {"message": "SDPs deleted on all nodes"}, 200

  def delete_fves_node(self, node_id):
    node_ip = self.rsdb["nodes"][node_id]["ip"]
    try:
      r = requests.delete("http://{}:5005/fves".format(node_ip))
    except requests.exceptions.ConnectionError as e:
      # handle error
      #logger.debug(str(e))
      logger.info("Node {} at {} not available for DELETE".format(node_id, node_ip))

  def delete_fves(self):
    process_list = []
    for node_id in self.rsdb["nodes"]:
      if self.rsdb["nodes"][node_id]["fves"]:
        p = Process(target=self.delete_fves_node, args=(node_id,))
        p.start()
        process_list.append(p)
    for p in process_list:
      p.join()
    return {"message": "FVEs deleted on all nodes"}, 200

  def delete_images_node(self, node_id):
    node_ip = self.rsdb["nodes"][node_id]["ip"]
    try:
      r = requests.delete("http://{}:5005/imgs".format(node_ip))
    except requests.exceptions.ConnectionError as e:
      # handle error
      #logger.debug(str(e))
      logger.info("Node {} at {} not available for DELETE".format(node_id, node_ip))

  def delete_images(self):
    process_list = []
    for node_id in self.rsdb["nodes"]:
      if self.rsdb["nodes"][node_id]["class"] == "I":
        p = Process(target=self.delete_images_node, args=(node_id,))
        p.start()
        process_list.append(p)
    for p in process_list: 
      p.join()
    return {"message": "Images deleted on all IaaS nodes"}, 200

# initialize database handler
rsdb = RSDB()

### Resource definition

class Test(Resource):
  def get(self):
    return {
      "message": "This endpoint ({}) is up!".format(os.path.basename(__file__)),
      "type": "ORD_TEST_OK"
    }

class FogNodeList(Resource):

  def get(self):
    resp = rsdb.get_node_list()
    #resp.update({"type": "ORD_NODE_LIST"})
    return resp

  def delete(self):
    rsdb.delete_apps()
    rsdb.delete_sdps()
    rsdb.delete_fves()
    rsdb.delete_images()
    rsdb.flush_db()
    return {
      "message": "Services deleted and database re-initialized",
      "type": "ORD_NDDB_DEL"
    }, 200

class FogNode(Resource):
  def get(self, node_id):
    resp, resp_code = rsdb.get_node(node_id)
    #resp.update({"type": "ORD_NODE_NDEF"})
    return resp, resp_code

class FogMeasurements(Resource):
  def get(self):
    resp = rsdb.get_measurements()
    #resp.update({"type": "ORD_MEAS"})
    return resp

class FogApplicationCatalog(Resource):
  def get(self):
    resp = rsdb.get_app_catalog()
    #resp.update({"type": "ORD_APP_CAT"})
    return resp

class FogApplicationList(Resource):
  def get(self):
    resp = rsdb.get_app_list()
    #resp.update({"type": "ORD_APP_LIST"})
    return resp
  def delete(self):
    resp = rsdb.delete_apps()
    #resp.update({"type": "ORD_APP_DEL"})
    return resp

class FogApplication(Resource):
  def get(self, app_id):
    resp = rsdb.get_app(app_id)
    #resp.update({"type": "ORD_APP"})
    return resp

class SoftDevPlatformCatalog(Resource):
  def get(self):
    resp = rsdb.get_sdp_catalog()
    #resp.update({"type": "ORD_SDP_CAT"})
    return resp

class SoftDevPlatformList(Resource):
  def get(self):
    resp = rsdb.get_sdp_list()
    #resp.update({"type": "ORD_SDP_LIST"})
    return resp
  def delete(self):
    resp = rsdb.delete_sdps()
    #resp.update({"type": "ORD_SDP_DEL"})
    return resp

class SoftDevPlatform(Resource):
  def get(self, sdp_id):
    resp = rsdb.get_sdp(sdp_id)
    #resp.update({"type": "ORD_SDP"})
    return resp

class FogVirtEngineCatalog(Resource):
  def get(self):
    resp = rsdb.get_fve_catalog()
    #resp.update({"type": "ORD_FVE_CAT"})
    return resp

class FogVirtEngineList(Resource):
  def get(self):
    resp = rsdb.get_fve_list()
    #resp.update({"type": "ORD_FVE_LIST"})
    return resp
    
  def delete(self):
    resp = rsdb.delete_fves()
    #resp.update({"type": "ORD_FVE_DEL"})
    return resp

class FogVirtEngine(Resource):
  def get(self, fve_id):
    resp = rsdb.get_fve(fve_id)
    #resp.update({"type": "ORD_FVE"})
    return resp

### MAIN

if __name__ == '__main__':

  if wait_remote:
    wait_for_remote_endpoint(iaas_mgmt_address, iaas_mgmt_port)

  ### API definition
  
  app = Flask(__name__)
  
  #@app.teardown_appcontext
  #def shutdown_session(exception=None):
  #  print("TEARDOWN!")
  
  api = Api(app)
  
  api.add_resource(Test, '/test')
  
  api.add_resource(FogNodeList, '/nodes')
  api.add_resource(FogNode, '/node/<node_id>')
  
  api.add_resource(FogMeasurements, '/meas')
  
  api.add_resource(FogApplicationCatalog, '/appcat')
  api.add_resource(FogApplicationList, '/apps')
  api.add_resource(FogApplication, '/app/<app_id>')
  
  api.add_resource(SoftDevPlatformCatalog, '/sdpcat')
  api.add_resource(SoftDevPlatformList, '/sdps')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')
  
  api.add_resource(FogVirtEngineCatalog, '/fvecat')
  api.add_resource(FogVirtEngineList, '/fves')
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

  app.run(host=ep_address, port=ep_port, debug=debug)

