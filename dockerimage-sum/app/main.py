import os

import flask
from flask_restful import Resource, Api
# from flask_qrcode import QRcode

from datetime import datetime


class Hello(Resource):
  def get(self):
    return {
      "message": "Hello World from Flask in a uWSGI Nginx Docker container"
    }


class Info(Resource):
  def get(self):
    return {
      "message": "I'm alive!",
      "time": f"{datetime.now():%c}"
    }


class Sum(Resource):
  def post(self):
    r_json = flask.request.get_json(force=True)
    try:
      i1 = int(r_json['input1'])
      i2 = int(r_json['input2'])
    except ValueError:
      return {
        "message": f"Invalid inputs"
      }, 404
    # i1 = int(r_json['input1'])
    # i2 = int(r_json['input2'])
    sum = i1+i2
    # print(f"Sum: {sum}")
    return {
      "message": "All done!",
      "result": str(sum)
    }


app = flask.Flask(__name__)

api = Api(app)
api.add_resource(Hello, '/hello')
api.add_resource(Info, '/info')
api.add_resource(Sum, '/sum')

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
