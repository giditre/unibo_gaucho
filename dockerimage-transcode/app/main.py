import os
import flask
from flask import send_file
from flask_restful import Resource, Api, reqparse
import werkzeug
from PIL import Image, UnidentifiedImageError

from datetime import datetime

class Info(Resource):

  def get(self):

    return {

      "message": "I'm alive!",
      "time": f"{datetime.now():%c}"

    }

class Transcode(Resource):

  def post(self):

    parse = reqparse.RequestParser()
    parse.add_argument('image', type=werkzeug.datastructures.FileStorage, location='files')
    args = parse.parse_args()
    image_file = args['image']
    image_file.save('/tmp/image')

    try:

      image = Image.open('/tmp/image')

    except UnidentifiedImageError:

      return {

      "message": "Invalid format!",

      }, 404

    if image.format == 'JPEG':

      return {

      "message": "Image already in jpg format!",

      }, 200

    else: 

      image.convert('RGB').save('/tmp/transcoded.jpg', format='JPEG')

      return send_file('/tmp/transcoded.jpg', mimetype='image/jpg')

app = flask.Flask(__name__)

api = Api(app)
api.add_resource(Info, '/info')
api.add_resource(Transcode, '/trn')

@app.route("/")
def main():
    index_path = os.path.join(app.static_folder, "index.html")
    return send_file(index_path)

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
