from multiprocessing import Pool
from multiprocessing import cpu_count
import time
import os

import flask
from flask_restful import Resource, Api

from datetime import datetime


class Info(Resource):
  def get(self):
    return {
      "message": "I'm alive!",
      "time": f"{datetime.now():%c}"
    }


class PythonSDP(Resource):
  def __init__(self):
    super().__init__()
    self.code = None
    self.output_lines = []

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

  def exec_code(self, code):
    exec(code, {'__builtins__': __builtins__}, {"print": self.store_output, "time": time.time, "sleep": time.sleep})

  def store_output(self, data):
    print(data)
    if isinstance(data, str):
      for line in data.split("\n"):
        self.output_lines.append(line)
    else:
      self.output_lines.append(str(data))

  def get_output(self):
    if not self.output_lines:
      return None
    return "\n".join(self.output_lines)
    
  def post(self):
    r_json = flask.request.get_json(force=True)
    try:
      code = r_json['code']
    except KeyError:
      return {
        "message": f"Invalid input"
      }, 404

    self.exec_code(code)

    result = self.get_output()

    if result is None:
      return {
        "message": "Problem with input or no output"
      }, 404
    
    return {
      "message": "All done!",
      "output": result
    }


app = flask.Flask(__name__)

api = Api(app)
api.add_resource(Info, '/info')

api.add_resource(PythonSDP, '/python')

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
