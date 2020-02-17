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

from pyzabbix import ZabbixAPI

### Logging setup

logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

### Command line argument parser

parser = argparse.ArgumentParser()

parser.add_argument("address", help="Endpoint IP address")
parser.add_argument("port", help="Endpoint TCP port")
parser.add_argument("--db-json", help="Database JSON file, default: rsdb.json", nargs="?", default="rsdb.json")
parser.add_argument("--imgmt-address", help="IaaS management endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
parser.add_argument("--imgmt-port", help="IaaS management endpoint TCP port, default: 5004", nargs="?", default=5004)
parser.add_argument("-w", "--wait-remote", help="Wait for remote endpoint(s), default: false", action="store_true", default=False)

args = parser.parse_args()

ep_address = args.address
ep_port = args.port
db_fname = args.db_json
iaas_mgmt_address = args.imgmt_address
iaas_mgmt_port = args.imgmt_port
wait_remote = args.wait_remote

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

  def get_metrics(self, node_id=None, search_str=""):
    fields = [ "hostid", "itemid", "name", "lastclock", "lastvalue", "units" ]
    return { item["itemid"] : { f: item[f] for f in fields } for item in self.zapi.item.get(filter={"hostid": node_id}, search={"name": "*{}*".format(search_str)}, searchWildcardsEnabled=True) }

  def get_utilization(self, node_id):
    return self.get_items(node_id, "utilization")

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
    
### manage database

class RSDB():

  def __init__(self):
    #with open("res_serv_database.json") as f:
    #  self.rsdb = json.load(f)

    # initialize nodes and apps databases as empty dicts
    self.rsdb = self.init_db()

    #self.known_services = [ self.rsdb["services"][s]["name"] for s in self.rsdb["services"] ]

    self.db_lock = threading.Lock()
  
    # write initial database
    #write_db_to_file(db_fname, self.rsdb, period=10)

    # define fields we expect to find in a node update packet
    self.node_fields = ["mac", "ipv4", "class", "apps", "SDPs", "FVEs", "av_res"]

    self.write_db = True

    self.collector = Zabbix()

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
    rsdb["SDP_catalog"] = sdp_cat["SDPs"]
    rsdb["FVE_catalog"] = fve_cat["FVEs"]

    rsdb["apps"] = deepcopy(rsdb["app_catalog"])
    for app in rsdb["app_catalog"]:
      rsdb["apps"][app]["nodes"] = []

    rsdb["SDPs"] = deepcopy(rsdb["SDP_catalog"])
    for sdp in rsdb["SDP_catalog"]:
      rsdb["SDPs"][sdp]["nodes"] = []

    rsdb["FVEs"] = deepcopy(rsdb["FVE_catalog"])
    for fve in rsdb["FVE_catalog"]:
      rsdb["FVEs"][fve]["nodes"] = []    

    return rsdb   

  def get_node_fields(self):
    return self.node_fields

  def get_node_list(self):
    self.rsdb["nodes"] = self.collector.get_nodes()
    return self.rsdb["nodes"]

  def get_node(self, node_id):
    if node_id in self.rsdb["nodes"]:
      return self.rsdb["nodes"][node_id], 200
    else:
      return {"message": "Node {} not in database, update database by performing GET /nodes and try again".format(node_id)}, 404

  def put_node(self, node_json):
    response_code = -1
    # generate deterministic UUID based on MAC address of node
    node_uuid = mac_to_uuid(node_json["mac"])
    # acquire the lock for the whole sequence of operations on the database
    with self.db_lock:
      # check if there is an entry for this node (identified by MAC-based UUID)
      if node_uuid not in self.rsdb["nodes"]:
        response_code = 201
        # create  entry
        self.rsdb["nodes"][node_uuid] = { "uuid": node_uuid }
        self.rsdb["nodes"][node_uuid]["name"] = "fn-{}".format(node_uuid[-4:])
        self.rsdb["nodes"][node_uuid]["url"] = "{}.fog.net".format(self.rsdb["nodes"][node_uuid]["name"])
        for field in self.node_fields:
          self.rsdb["nodes"][node_uuid][field] = node_json[field]
        # insert timestamp
        self.rsdb["nodes"][node_uuid]["last_heard"] = int(time())
      else:
        response_code = 200
        # update entry
        for field in [ f for f in self.node_fields if f not in ["mac"] ]:
          self.rsdb["nodes"][node_uuid][field] = node_json[field]
        # insert timestamp
        self.rsdb["nodes"][node_uuid]["last_heard"] = int(time())

      # update apps database
      for app in self.rsdb["nodes"][node_uuid]["apps"]:
        if app in self.rsdb["apps"]:
          if node_uuid not in self.rsdb["apps"][app]["nodes"]:
            self.rsdb["apps"][app]["nodes"].append(node_uuid)
        else:
          self.rsdb["apps"][app] = deepcopy(self.rsdb["app_catalog"][app])
          self.rsdb["apps"][app]["nodes"] = [node_uuid]

      # update FVEs database
      if self.rsdb["nodes"][node_uuid]["FVEs"]:
        for fve in self.rsdb["nodes"][node_uuid]["FVEs"]:
          if fve in self.rsdb["FVEs"]:
            if node_uuid not in self.rsdb["FVEs"][fve]["nodes"]:
              self.rsdb["FVEs"][fve]["nodes"].append(node_uuid)
          else:
            self.rsdb["FVEs"][fve] = deepcopy(self.rsdb["FVE_catalog"][fve])
            self.rsdb["FVEs"][fve]["nodes"] = [node_uuid]

      if self.write_db:
        # update stored database
        with open("debug_rsdb.json", "w") as f:
          json.dump(self.rsdb, f)

    return self.rsdb["nodes"][node_uuid]["name"], response_code

  def flush_db(self):
    with self.db_lock:
      self.rsdb = self.init_db()
    return 204

  def get_app_catalog(self):
    return self.rsdb["app_catalog"]

  def get_app_list(self):
    return self.rsdb["apps"]

  def get_app(self, app_id):
    if app_id not in self.rsdb["apps"]:
      abort(404, message="Application {} not found.".format(app_id))
    return self.rsdb["apps"][app_id]

  def get_sdp_catalog(self):
    return self.rsdb["SDP_catalog"]

  def get_sdp_list(self):
    return self.rsdb["SDPs"]

  def get_sdp(self, sdp_id):
    if sdp_id not in self.rsdb["SDPs"]:
      abort(404, message="SDP {} not found.".format(sdp_id))
    return self.rsdb["SDPs"][sdp_id]

  def get_fve_catalog(self):
    return self.rsdb["FVE_catalog"]

  def get_fve_list(self):
    return self.rsdb["FVEs"]

  def get_fve(self, fve_id):
    if fve_id not in self.rsdb["FVEs"]:
      abort(404, message="FVE {} not found.".format(fve_id))
    return self.rsdb["FVEs"][fve_id]

# initialize database handler
rsdb = RSDB()

### Resource definition

class Test(Resource):
  def get(self):
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class FogNodeList(Resource):

  def get(self):
    return rsdb.get_node_list()

  def post(self):

    # TODO
    #fognodes_dict = { h["hostid"] : h for h in zapi.host.get(search={"name": "Zabbix Server"}, excludeSearch=True) }

    json_data = request.get_json(force=True)
    node = {}
    for field in rsdb.get_node_fields():
      try:
        #if not json_data[field]:
        #  raise ValueError
        node[field] = json_data[field]
      except KeyError:
        print("Request does not specify required field {}.".format(field))
        abort(400, message="Request does not specify required field {}.".format(field))
      #except ValueError:
      #  abort(400, message="Request does not specify value for required field {}.".format(field))
    node_name, response_code = rsdb.put_node(node)
    return {"name": node_name}, response_code

  def delete(self):
    #json_data = request.get_json(force=True)
    #field = "mac"
    #try:
    #  if not json_data[field]:
    #    raise ValueError
    #except KeyError:
    #  abort(400, message="Request does not specify required field {}.".format(field))
    #except ValueError:
    #  abort(400, message="Request does not specify value for required field {}.".format(field))    
    return rsdb.flush_db()

class FogNode(Resource):
  def get(self, node_id):
    resp, resp_code = rsdb.get_node(node_id)
    return resp, resp_code

class FogApplicationCatalog(Resource):
  def get(self):
    return rsdb.get_app_catalog()

class FogApplicationList(Resource):
  def get(self):
    return rsdb.get_app_list()

class FogApplication(Resource):
  def get(self, app_id):
    return rsdb.get_app(app_id)

class SoftDevPlatformCatalog(Resource):
  def get(self):
    return rsdb.get_sdp_catalog()

class SoftDevPlatformList(Resource):
  def get(self):
    return rsdb.get_sdp_list()

class SoftDevPlatform(Resource):
  def get(self, sdp_id):
    return rsdb.get_sdp(sdp_id)

class FogVirtEngineCatalog(Resource):
  def get(self):
    return rsdb.get_fve_catalog()

class FogVirtEngineList(Resource):
  def get(self):
    return rsdb.get_fve_list()

class FogVirtEngine(Resource):
  def get(self, fve_id):
    return rsdb.get_fve(fve_id)

### API definition

app = Flask(__name__)
api = Api(app)

api.add_resource(Test, '/test')

api.add_resource(FogNodeList, '/nodes')
api.add_resource(FogNode, '/node/<node_id>')

api.add_resource(FogApplicationCatalog, '/appcat')
api.add_resource(FogApplicationList, '/apps')
api.add_resource(FogApplication, '/app/<app_id>')

api.add_resource(SoftDevPlatformCatalog, '/sdpcat')
api.add_resource(SoftDevPlatformList, '/sdps')
api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')

api.add_resource(FogVirtEngineCatalog, '/fvecat')
api.add_resource(FogVirtEngineList, '/fves')
api.add_resource(FogVirtEngine, '/fve/<fve_id>')

### MAIN

if __name__ == '__main__':

  if wait_remote:
    wait_for_remote_endpoint(iaas_mgmt_address, iaas_mgmt_port)

  app.run(host=ep_address, port=ep_port, debug=True)

