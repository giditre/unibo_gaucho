from flask import Flask, request
from flask_restful import Resource, Api, reqparse, abort
import json
import argparse
import requests
import logging
import random
from time import sleep
import os
from werkzeug.security import check_password_hash
from functools import wraps

### Logging setup

logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

###

def authenticate(function):

  @wraps(function)
  def wrapper(*args, **kwargs):

    auth = request.authorization

    if not auth or not auth.username or not auth.password:
      return {"message": "Authorization required"}, 401

    # load db file
    with open("db_users.json") as f:
      user_db = json.load(f)

    # check if user exists in db
    for uid in user_db:
      if user_db[uid]["name"] == auth.username:
        # found it!
        reg_user_name = user_db[uid]["name"]
        reg_user_pwd = user_db[uid]["password"]
        if check_password_hash(reg_user_pwd, auth.password):
          # success!
          #return reg_user_name
          return function(*args, **kwargs)
        else:
          # user unauthorized
          return {"message": "Unauthorized user"}, 401

    # user not found
    return {"message": "Bad authorization"}, 401

  return wrapper

### Resource definition

class Test(Resource):
  @authenticate
  def get(self):
    ##logger.debug(request.authorization)
    #auth_user = authenticate(request.authorization)
    #if not auth_user:
    #  return {"message": "Bad authentication"}, 401
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class FogApplicationList(Resource):
  def get(self):
    # get app list from database
    r = requests.get("http://{}:{}/appcat".format(db_address, db_port))
    return r.json(), r.status_code

class FogApplication(Resource):
  def get(self, app_id):
    # get node id from broker
    r = requests.get("http://{}:{}/app/{}".format(broker_address, broker_port, app_id))
    return r.json(), r.status_code

class SoftDevPlatformList(Resource):
  def get(self):
    # get SDP list from database
    r = requests.get("http://{}:{}/sdpcat".format(db_address, db_port))
    return r.json(), r.status_code

class SoftDevPlatform(Resource):
  def get(self, sdp_id):
    # get node id from broker
    r = requests.get("http://{}:{}/sdp/{}".format(broker_address, broker_port, sdp_id))
    return r.json(), r.status_code

class FogVirtEngineList(Resource):
  def get(self):
    # get fve list from database
    r = requests.get("http://{}:{}/fvecat".format(db_address, db_port))
    return r.json(), r.status_code

class FogVirtEngine(Resource):
  def get(self, fve_id):
    # get node id from broker
    r = requests.get("http://{}:{}/fve/{}".format(broker_address, broker_port, fve_id))
    return r.json(), r.status_code

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

### API definition

app = Flask(__name__)
api = Api(app)

api.add_resource(Test, '/test')

api.add_resource(FogApplicationList, '/apps')
api.add_resource(FogApplication, '/app/<app_id>')

api.add_resource(SoftDevPlatformList, '/sdps')
api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')

api.add_resource(FogVirtEngineList, '/fves')
api.add_resource(FogVirtEngine, '/fve/<fve_id>')

### MAIN

if __name__ == '__main__':

  ### Command line argument parsing
  
  parser = argparse.ArgumentParser()
  
  parser.add_argument("address", help="Endpoint IP address")
  parser.add_argument("port", help="Endpoint TCP port")
  parser.add_argument("--db-address", help="Database endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
  parser.add_argument("--db-port", help="Database endpoint TCP port, default: 5003", nargs="?", default=5003)
  parser.add_argument("--broker-address", help="Broker endpoint IP address, default: 127.0.0.1", nargs="?", default="127.0.0.1")
  parser.add_argument("--broker-port", help="Broker endpoint TCP port, default: 5002", nargs="?", default=5002)
  parser.add_argument("-w", "--wait-remote", help="Wait for remote endpoint(s), default: false", action="store_true", default=False)
  parser.add_argument("-d", "--debug", help="Run in debug mode, default: false", action="store_true", default=False)
  
  args = parser.parse_args()
  
  ep_address = args.address
  ep_port = args.port
  db_address = args.db_address
  db_port = args.db_port
  broker_address = args.broker_address
  broker_port = args.broker_port
  wait_remote = args.wait_remote
  debug = args.debug

  if wait_remote:
    wait_for_remote_endpoint(db_address, db_port)
    wait_for_remote_endpoint(broker_address, broker_port)

  app.run(host=ep_address, port=ep_port, debug=debug, ssl_context='adhoc')

