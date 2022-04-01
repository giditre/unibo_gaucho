import flask
from flask_restful import Resource, Api
import logging
from logging.config import fileConfig
from pathlib import Path
import forch #to remove
import psutil
#import json

def retrieve_metrics():

  metrics = {

    key:{} for key in ["cpu", "ram", "disk", "net"]
  
  }

  logger.info("Retrieving metrics...")

  for i, value in enumerate(psutil.cpu_percent(interval=1, percpu=True)):

    metrics["cpu"][f"cpu{i} usage"] = value

  metrics["ram"]["available"] = psutil.virtual_memory().percent

  metrics["disk"]["available"] = psutil.disk_usage('/').percent

  for key, value in psutil.net_if_stats().items():

    if key != "lo" and key != "docker0":

      metrics["net"][key + " mtu"] = value.mtu

  if metrics:

    return metrics

  else:

    return None

fileConfig(str(Path(__file__).parent.parent.parent.parent.joinpath("main/src/main/logging.ini"))) #better way to do this?
logger = logging.getLogger(__name__)
logger.info(f"Load {__name__} with {logger}")

class Metrics(Resource):

  def get(self):

    if metrics:=retrieve_metrics():

      return {

        "message": f'{metrics}',

      }, 200

    else:

       return {

          "message": "Cannot retrieve any metric!",

       }, 404

if __name__ == "__main__":

  local_config = forch.get_local_config(Path(__file__).parent.parent.parent.parent.joinpath("main/src/main/main.ini").absolute())
  logger.debug(f"Config: {dict(local_config.items())}") #config_parser

  app = flask.Flask(__name__)

  api = Api(app)
  api.add_resource(Metrics, '/metrics')

  logger.info("Starting server...")

  try:

    app.run(host=local_config.get("address"), port=local_config.getint("forch_port"), debug=local_config.getboolean("debug")) #better way to do this?

  except KeyboardInterrupt:

    pass

  finally:

    logger.info("Cleanup after interruption")