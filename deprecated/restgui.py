from http.server import BaseHTTPRequestHandler, HTTPServer
from signal import pause
from socket import gethostname
from distutils.dir_util import copy_tree
import os
import shutil
from threading import Thread
import logging
import argparse
from time import sleep
import requests
import json
from urllib.parse import urlparse, parse_qs

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

### Logging setup

logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

### Command line argument parser

default_address = "0.0.0.0"
default_port = 3300

parser = argparse.ArgumentParser()
  
parser.add_argument("-a", "--address", help="IP address of this server. Default: {}".format(default_address), nargs="?", default=default_address)
parser.add_argument("-p", "--port", help="TCP port of this server. Default: {}".format(default_port), type=int, nargs="?", default=default_port)
parser.add_argument("-d", "--debug", help="Run in debug mode.", action="store_true", default=False)

args = parser.parse_args()

address = args.address
port = args.port
debug = args.debug

###

endpoints = {
  "/apps": "",
  "/app": "",
  "/sdps": "",
  "/fves": ""
}


###

def shell_cmd(cmd): 
  logging.debug("shell command: {}".format(cmd))
  return os.system(cmd)

###

class MyServer(BaseHTTPRequestHandler):
  """ A special implementation of BaseHTTPRequestHander  """

  def do_HEAD(self):
    """ do_HEAD() can be tested use curl command 
        'curl -I http://server-ip-address:port' 
    """
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()

  def redirect_to(self, path):
    self.send_response(302)
    self.send_header("Location", "/")
    self.end_headers()

  def external_get(self, *args, **kwargs):
    r = requests.get(*args, **kwargs)
    return json.dumps(r.json(), indent=2)

  def parse_path(self, path):
    path, query_string = path.split("?")
    parameters = { k: v[0] for k,v in parse_qs(query_string).items() }
    return path, parameters

  #<input type="radio" id="male" name="gender" value="male">
  #<label for="male">Male</label><br>
  def radio_button(self, button_id, param_name, param_value, button_label):
    radio_button = """<input type="radio" id="{0}" name="{1}" value="{2}"><label for="{0}">{3}</label><br>""".format(button_id, param_name, param_value, button_label)
    return radio_button

  def create_form_radio(self, endpoint, items_key="items"):
    items_dict = json.loads(endpoints[endpoint])
    items_list = items_dict[items_key]
    output = """<form action="/app">"""

    for item in items_list:
      item_id = item["id"]
      output += self.radio_button(item_id.lower(), "itemid", item_id, item_id)

    output += """<input type="submit" value="Request"></form>"""

    return output

  def do_GET(self):
  
    global endpoints

    html = '''
<!DOCTYPE html>
<html>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<head>

<style>
.left {{
  margin: 10px;
  width: 60%;
  padding: 10px;
  text-align:left;
}}
</style>

<style>
.center {{
  margin: auto;
  width: 60%;
  padding: 10px;
  text-align:center;
}}
</style>

<style>
.centerbox {{
  margin: auto;
  width: 90%;
  padding: 10px;
  border: 3px solid #73AD21;
  text-align:center;
}}
</style>

<style>
.truestyle:link, .truestyle:visited {{
  background-color: green;
  color: white;
  padding: 15px 25px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
}}

.truestyle:hover, .truestyle:active {{
  background-color: darkgreen;
}}
</style>

<style>
.falsestyle:link, .falsestyle:visited {{
  background-color: red;
  color: white;
  padding: 15px 25px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
}}

.falsestyle:hover, .falsestyle:active {{
  background-color: darkred;
}}
</style>

</head>

<body>

<div class="centerbox">
<h1>{}</h1>
</div>

<div class="left">
<p>
<a href="/apps">APPS</a><br>
<pre>{}</pre>
{}
<pre>{}</pre>
</div>

<div class="left">
<p>
<a href="/sdps">SDPS</a><br>
<pre>{}</pre>
</div>

<div class="left">
<p>
<a href="/fves">FVES</a><br>
<pre>{}</pre>
</div>

</body>
</html>
    '''

    if self.path == "/":
      self.do_HEAD()
      
      self.wfile.write(
        html.format(
          gethostname(),
          endpoints["/apps"],
          self.create_form_radio("/apps") if endpoints["/apps"] else "",
          endpoints["/app"],
          endpoints["/sdps"],
          endpoints["/fves"]
        ).encode("utf-8"))

    elif self.path in endpoints:
      endpoints[self.path] = self.external_get("https://127.0.0.1:5001" + self.path, auth=("admin", "gauchoadmin123"), verify=False)
      self.redirect_to("/")

    elif self.path.startswith("/app?"):
      print(self.path)
      path, parameters = self.parse_path(self.path)
      print(path, parameters)
      r = self.external_get("https://127.0.0.1:5001" + path + "/{}".format(parameters["itemid"]), auth=("admin", "gauchoadmin123"), verify=False)
      print(r)
      endpoints["/app"] = r
      self.redirect_to("/")

    else:
      #super().do_GET(self)
      pass

if __name__ == '__main__':

    http_server = HTTPServer((address, port), MyServer)
    logger.debug("Server Starts - {}:{}".format(address, port))

    try:
      http_server.serve_forever()
    except KeyboardInterrupt:
      http_server.server_close()

