from multiprocessing import Pool
from multiprocessing import cpu_count
import time
import os

import flask
from flask_restful import Resource, Api
# from flask_qrcode import QRcode

from datetime import datetime


class Info(Resource):
  def get(self):
    return {
      "message": "I'm alive!",
      "time": f"{datetime.now():%c}"
    }


class Stress(Resource):
  def __init__(self):
    super().__init__()
    self.n_cpu = None
    self.timeout = None

  def start(self, x):
    end_t = time.time() + self.timeout
    try:
      while True:
        if time.time() > end_t:
          break
        x*x # could be any number
    except KeyboardInterrupt:
      pass

  def stress(self, load, timeout):
    self.n_cpu = int( cpu_count() * load/100 )
    self.timeout = timeout

    if self.n_cpu > 0:
      processes = self.n_cpu
      print(f"Stressing {processes} CPUs for {timeout} seconds...")
      pool = Pool(processes)
      pool.map(self.start, range(processes))

    return self.n_cpu

  def post(self):
    r_json = flask.request.get_json(force=True)
    try:
      load = int(r_json['load'])
      timeout = int(r_json['timeout'])
    except ValueError:
      return {
        "message": f"Invalid inputs"
      }, 404

    n_cpu = self.stress(load, timeout)

    if n_cpu == 0:
      return {
        "message": "Set higher load",
        "n_cpu": n_cpu
      }, 404
    
    return {
      "message": "All done!",
      "n_cpu": n_cpu
    }
      


app = flask.Flask(__name__)

api = Api(app)
api.add_resource(Info, '/info')

api.add_resource(Stress, '/stress')

@app.route("/")
def main():
    index_path = os.path.join(app.static_folder, "index.html")
    return flask.send_file(index_path)

# Everything not declared before (not a Flask route / API endpoint)...
@app.route("/<path:path>")
def route_frontend(path):
    # ...could be a static file needed by the front end that
    # doesn't use the `static` path (like in `<script src="bundle.js">`)
    file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(file_path):
        return flask.send_file(file_path)
    # ...or should be handled by the SPA's "router" in front end
    else:
        index_path = os.path.join(app.static_folder, "index.html")
        return flask.send_file(index_path)

if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host="0.0.0.0", debug=True, port=80)
