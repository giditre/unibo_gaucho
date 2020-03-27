import time
import requests
import json
import datetime
import argparse

def print_flush(*args, **kwargs):
  kwargs["flush"] = True
  print(*args, **kwargs)

parser = argparse.ArgumentParser()
  
#parser.add_argument("-a", "--app-id", help="Fog Application ID, default: FA002", type=int, nargs="?", default=3)
parser.add_argument("--pre-delete", help="DELETE before starting allocatio, default: False", action="store_true", default=False)
parser.add_argument("--post-delete", help="DELETE after gathering measurements, default: False", action="store_true", default=False)

args = parser.parse_args()
print_flush("CLI args: {}".format(vars(args)))

#app_id = args.app_id
pre_delete = args.pre_delete
post_delete = args.post_delete

if pre_delete:
  #curl -X DELETE http://127.0.0.1:5003/nodes
  print_flush("DELETE", "http://127.0.0.1:5003/nodes")
  r = requests.delete("http://127.0.0.1:5003/nodes")
  print_flush("Sleep for 240 seconds")
  time.sleep(240)

#curl http://192.168.10.117:5001/apps
print_flush("GET", "http://192.168.10.117:5001/nodes")
r = requests.get("http://192.168.10.117:5001/apps")
time.sleep(1)

# request the allocation of new service
print_flush("GET", "http://192.168.10.117:5001/app/FA002")
r = requests.get("http://192.168.10.117:5001/app/FA002")
resp_json = r.json()
print_flush(json.dumps(resp_json, indent=2))
time.sleep(1)

while r.status_code in [200, 201]:
  # gather data on deployed service
  node_ip = resp_json["node_ip"]
  serv_port = resp_json["service_port"]

  # start new service
  url = "http://{}:{}/app/FA002".format(node_ip, serv_port)
  data_json = {"timeout":10000, "cpu":2}
  print_flush("POST", data_json, url)
  r = requests.post(url, json=data_json)
  resp_json = r.json()
  print_flush(json.dumps(resp_json, indent=2))
  time.sleep(1)

  print_flush("Sleep for 120 seconds")
  time.sleep(120)

  # request the allocation of new service
  print_flush("GET", "http://192.168.10.117:5001/app/FA002")
  r = requests.get("http://192.168.10.117:5001/app/FA002")
  resp_json = r.json()
  print_flush(json.dumps(resp_json, indent=2))
  time.sleep(10)

print_flush("Sleep for 240 seconds")
time.sleep(240)

# get measurements
print_flush("GET", "http://127.0.0.1:5003/meas")
r = requests.get("http://127.0.0.1:5003/meas")
time.sleep(1)
with open("../gauchotest/get_meas_test_{0:%Y%m%d_%H%M%S}.json".format(datetime.datetime.now()), "w") as f:
  json.dump(r.json(), f)

if post_delete:
  #curl -X DELETE http://127.0.0.1:5003/nodes
  print_flush("DELETE", "http://127.0.0.1:5003/nodes")
  r = requests.delete("http://127.0.0.1:5003/nodes")
  time.sleep(1)

