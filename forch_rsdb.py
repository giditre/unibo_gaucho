from flask import Flask, request, jsonify
from flask_restful import Resource, Api, reqparse, abort
import json
import argparse
from time import time
import uuid
import logging
import os
import threading

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
parser.add_argument("--db-json", help="Database JSON file", nargs="?", default="rsdb.json")

args = parser.parse_args()

ep_address = args.address
ep_port = args.port
db_fname = args.db_json

### user functions

def mac_to_uuid(mac):
  # generate deterministic UUID based on MAC address of node
  return str(uuid.uuid3(uuid.NAMESPACE_DNS, mac))

def write_db_to_file(fname, db_json, period=0):
  with open(fname, "w") as f:
    json.dump(db_json, f)
  if period:
    threading.Timer(period, write_db_to_file, args=[fname, db_json, period]).start()
    
### manage database

class RSDB():

  def __init__(self):
    #with open("res_serv_database.json") as f:
    #  self.rsdb = json.load(f)

    # initialize nodes and apps databases as empty dicts
    self.rsdb = self.init_db()

    #self.known_services = [ self.rsdb["services"][s]["name"] for s in self.rsdb["services"] ]

    #self.db_lock = threading.Lock()
  
    # write initial database
    #write_db_to_file(db_fname, self.rsdb, period=10)

    # define fields we expect to find in a node update packet
    self.node_fields = ["mac", "class", "apps", "SDP", "FVE", "av_res"]

  def init_db(self):
    rsdb = { "nodes": {}, "apps": {}, "app_catalog": {} }
    # load apps from file and populate catalog
    with open("db_apps.json") as f:
      app_catalog = json.load(f)
    rsdb["app_catalog"] = app_catalog["apps"]
    #for a in app_catalog["services"]:
    #  # generate random UUID for service
    #  u = str(uuid.uuid4())
    #  rsdb["services"][u] = s
    #  rsdb["services"][u]["uuid"] = u
    return rsdb   

  def get_node_fields(self):
    return self.node_fields

  def get_node_list(self):
    return self.rsdb["nodes"]

  def get_node(self, node_id):
    if node_id not in self.rsdb["nodes"]:
      abort(404, message="Node {} not found.".format(node_id))
    return self.rsdb["nodes"][node_id]

  def put_node(self, node_json):
    response_code = -1
    # generate deterministic UUID based on MAC address of node
    node_uuid = mac_to_uuid(node_json["mac"])
    # check if there is an entry for this node (identified by MAC-based UUID)
    if node_uuid not in self.rsdb["nodes"]:
      response_code = 201
      # create  entry
      self.rsdb["nodes"][node_uuid] = { "uuid": node_uuid }
      for field in self.node_fields:
        self.rsdb["nodes"][node_uuid][field] = node_json[field]
      # insert timestamp
      self.rsdb["nodes"][node_uuid]["last_heard"] = int(time())
      ## scan services and group nodes by service
      #for app_id in self.rsdb["services"]:
      #  s_name = self.rsdb["services"][s_id]["name"]
      #  self.rsdb["services"][s_id]["nodes"] = []
      #  for n_id in self.rsdb["nodes"]:
      #    if self.rsdb["nodes"][n_id]["service"] == s_name:
      #      self.rsdb["services"][s_id]["nodes"].append(n_id)
    else:
      response_code = 200
      # update entry
      for field in [ f for f in self.node_fields if f not in ["mac", "class", "SDP", "FVE"] ]:
        self.rsdb["nodes"][node_uuid][field] = node_json[field]
      # insert timestamp
      self.rsdb["nodes"][node_uuid]["last_heard"] = int(time())

    # update apps database
    for app in self.rsdb["nodes"][node_uuid]["apps"]:
      if app in self.rsdb["apps"]:
        if node_uuid not in self.rsdb["apps"][app]["nodes"]:
          self.rsdb["apps"][app]["nodes"].append(node_uuid)
      else:
        self.rsdb["apps"][app] = self.rsdb["app_catalog"][app]
        self.rsdb["apps"][app]["nodes"] = [node_uuid]

    ## update stored database
    #with open(db_fname, "w") as f:
    #  json.dump(self.rsdb, f)

    return response_code

  def flush_db(self):
    self.rsdb = self.init_db()
    return 204

  def get_app_list(self):
    return self.rsdb["apps"]

  def get_app(self, app_id):
    if app_id not in self.rsdb["apps"]:
      abort(404, message="Application {} not found.".format(app_id))
    return self.rsdb["apps"][app_id]

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
    json_data = request.get_json(force=True)
    node = {}
    for field in rsdb.get_node_fields():
      try:
        #if not json_data[field]:
        #  raise ValueError
        node[field] = json_data[field]
      except KeyError:
        abort(400, message="Request does not specify required field {}.".format(field))
      #except ValueError:
      #  abort(400, message="Request does not specify value for required field {}.".format(field))
    response_code = rsdb.put_node(node)
    return '', response_code

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
    return rsdb.get_node(node_id)

class FogApplicationList(Resource):
  def get(self):
    return rsdb.get_app_list()

class FogApplication(Resource):
  def get(self, app_id):
    return rsdb.get_app(app_id)

### API definition

app = Flask(__name__)
api = Api(app)

api.add_resource(Test, '/', '/test')

api.add_resource(FogNodeList, '/nodes')
api.add_resource(FogNode, '/node/<node_id>')

api.add_resource(FogApplicationList, '/apps')
api.add_resource(FogApplication, '/app/<app_id>')


### MAIN

if __name__ == '__main__':
  app.run(host=ep_address, port=ep_port, debug=True)

