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
parser.add_argument("--db-port", help="Database endpoint TCP port", nargs="?", default=5000)

args = parser.parse_args()

ep_address = args.address
ep_port = args.port
db_address = args.db_address
db_port = args.db_port

### Resource definition

class Test(Resource):
  def get(self):
    return {"message": "This endpoint ({}) is up!".format(os.path.basename(__file__))}

class FogNodeList(Resource):
  def get(self):
    return requests.get("http://{}:{}/nodes".format(db_address, db_port)).json()

class FogNode(Resource):
  def get(self, node_id):
    return requests.get("http://{}:{}/node/{}".format(db_address, db_port, node_id)).json()

class FogApplicationList(Resource):
  def get(self):
    return requests.get("http://{}:{}/apps".format(db_address, db_port)).json()

class FogApplication(Resource):
  def get(self, app_id):
    return requests.get("http://{}:{}/app/{}".format(db_address, db_port, app_id)).json()

def wait_for_remote_endpoint(ep_address, ep_port):
  url = "http://{}:{}/test".format(ep_address, ep_port)
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

api.add_resource(Test, '/', '/test')

api.add_resource(FogNodeList, '/nodes')
api.add_resource(FogNode, '/node/<node_id>')

api.add_resource(FogApplicationList, '/apps')
api.add_resource(FogApplication, '/app/<app_id>')


### MAIN

if __name__ == '__main__':

  wait_for_remote_endpoint(db_address, db_port)

  app.run(host=ep_address, port=ep_port, debug=True)

