from flask import Flask
from flask_restful import Resource, Api, reqparse, abort
import json
import argparse
import requests
import logging
import random
from time import sleep
import os

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

parser.add_argument("address", help="Endpoint IP address")
parser.add_argument("port", help="Endpoint TCP port")
parser.add_argument("--db-address", help="Database endpoint IP address", nargs="?", default="127.0.0.1")
parser.add_argument("--db-port", help="Database endpoint TCP port", nargs="?", default=5003)
parser.add_argument("--broker-address", help="Broker endpoint IP address", nargs="?", default="127.0.0.1")
parser.add_argument("--broker-port", help="Broker endpoint TCP port", nargs="?", default=5002)

args = parser.parse_args()

ep_address = args.address
ep_port = args.port
db_address = args.db_address
db_port = args.db_port
broker_address = args.broker_address
broker_port = args.broker_port

### Resource definition

class Test(Resource):
  def get(self):
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


### MAIN

if __name__ == '__main__':

  wait_for_remote_endpoint(db_address, db_port)
  wait_for_remote_endpoint(broker_address, broker_port)

  app.run(host=ep_address, port=ep_port, debug=True)

