#!/usr/bin/python3

import time
import requests
import json
import datetime
import argparse
import sys
import os

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def print_flush(*args, **kwargs):
  kwargs["flush"] = True
  print(*args, **kwargs)

parser = argparse.ArgumentParser()

parser.add_argument("allocation_get", help="Path to the resource allocation request, in the form /<path")
parser.add_argument("-p", "--preliminary_get", help="Path to the preliminary request, in the form /<path", required=False)

parser.add_argument("--fua-url", help="URL of the Fog User Access, in the form https://<hostname>:<port>", required=True)
parser.add_argument("--fua-user", help="User for the Fog User Access", required=True)
parser.add_argument("--fua-password", help="Password for the Fog User Access", required=True) 
parser.add_argument("--fgw-url", help="URL of the Fog Gateway, in the form https://<hostname>:<port>/<path>", required=False)
parser.add_argument("--fgw-user", help="User for the Fog Gateway, defaults to Fog User Access user if not specified", required=False)
parser.add_argument("--fgw-password", help="Password for the Fog Gateway, defaults to Fog User Access password if not specified", required=False)
parser.add_argument("--fomg-url", help="URL of the FORCH Management, in the form https://<hostname>:<port>/<path>", required=True)
parser.add_argument("--fomg-user", help="User for the FORCH Management, defaults to Fog User Access user if not specified", required=False)
parser.add_argument("--fomg-password", help="Password for the Fog Management, defaults to Fog User Access password if not specified", required=False)
parser.add_argument("-d", "--service-data", help="Service data to be passed to the request starting the service, default: {}", nargs="?", default="{}")
parser.add_argument("--pre-delete", help="DELETE before starting allocation, default: False", action="store_true", default=False)
parser.add_argument("--post-delete", help="DELETE after gathering measurements, default: False", action="store_true", default=False)
parser.add_argument("--test-delete", help="Stop fog node processes after getting measurements, default: False", action="store_true", default=False)
parser.add_argument("-y", "--assume-yes", help="Automatic yes to prompts, default: False", action="store_true", default=False)

parser.add_argument("--cycle-delete", help="DELETE at the end of every cycle, default: False", action="store_true", default=False)
parser.add_argument("-n", "--num-cycles", help="Number of measurement cycles", type=int, nargs="?", default=100)

parser.add_argument("--node-list", help="List of comma-separated Fog Node ID to be activated later", required=False)
parser.add_argument("--nnic", "--new-node-interval-cycles", help="Activates new node every n cycles", type=int, nargs="?", default=3)
parser.add_argument("-e", "--end-cycles", help="Number of cycles to perform after node_list is empty", type=int, nargs="?", default=7)

default_output_fname = "res_" + os.path.basename(__file__).split("_")[0] + "_" + "{0:%Y%m%d_%H%M%S}".format(datetime.datetime.now()) + ".json"
parser.add_argument("-o", "--output-fname", help="Output file name, defaults to {}".format(default_output_fname), nargs="?", default=default_output_fname)

args = parser.parse_args()
print_flush("CLI args: {}".format(vars(args)))

if not args.assume_yes:
  c = input("Confirm? [y/n] ")
  if c != "y":
    sys.exit("Aborted.")

#app_id = args.app_id
fua_url = args.fua_url.strip("/")
fua_user = args.fua_user
fua_password = args.fua_password
fomg_url = args.fomg_url.strip("/")
fomg_user = args.fomg_user if args.fomg_user else fua_user
fomg_password = args.fomg_password if args.fomg_password else fua_password
if args.fgw_url:
  fgw_url = args.fgw_url.strip("/")
  fgw_user = args.fgw_user if args.fgw_user else fua_user
  fgw_password = args.fgw_password if args.fgw_password else fua_password
pre_delete = args.pre_delete
post_delete = args.post_delete
test_delete = args.test_delete

preliminary_get = args.preliminary_get
allocation_get = args.allocation_get
service_data_json = json.loads(args.service_data)

cycle_delete = args.cycle_delete
n_cycles = args.num_cycles

new_node_id_list = list(args.node_list.split(",")) if args.node_list else []
new_node_int_cycles = args.nnic
end_cycles = args.end_cycles

test_node_id_list = list(args.node_list.split(",")) if args.node_list else []

output_fname = args.output_fname

if pre_delete:
  #curl -X DELETE http://127.0.0.1:5003/nodes
  url = fomg_url + "/127.0.0.1/5003/nodes"
  print_flush("DELETE", url)
  r = requests.delete(url, auth=(fomg_user, fomg_password), verify=False)

  print_flush("Sleep for 4 minutes")
  time.sleep(240)

# start measuring

print_flush("\n### START MEASUREMENTS ###\n")

remaining_cycles = n_cycles
i = 0

while remaining_cycles > 0:

  # increment cycle index
  i += 1

  print_flush("\n# Cycle {} ({} remaining)\n".format(i, remaining_cycles))

  if preliminary_get:
    url = fua_url + preliminary_get
    print_flush("GET", url)
    r = requests.get(url, auth=(fua_user, fua_password), verify=False)
    time.sleep(1)

  # request the allocation of new service
  url = fua_url + allocation_get
  print_flush("GET", url)
  r = requests.get(url, auth=(fua_user, fua_password), verify=False)
  resp_json = r.json()
  print_flush(json.dumps(resp_json, indent=2))

  time.sleep(1)

  # if allocation was successful, activate new service
  if r.status_code  in [200, 201]:
    node_id = resp_json["node_id"]
    serv_port = resp_json["service_port"]
    url = "{}/{}/{}/{}".format(fgw_url, node_id, serv_port, allocation_get.strip("/").replace("/", "-"))
    print_flush("POST", url)
    r = requests.post(url, json=service_data_json, auth=(fgw_user, fgw_password), verify=False)
    resp_json = r.json()
    print_flush(json.dumps(resp_json, indent=2))

    time.sleep(1)

  # on some cycles activate a new fog node
  if i % new_node_int_cycles == 0 and new_node_id_list:
    node_id = new_node_id_list.pop(0)
    url = fgw_url + "/" + node_id + "/8000"
    print_flush("GET", url)
    r = requests.get(url, auth=(fgw_user, fgw_password), verify=False)
    if not new_node_id_list:
      print_flush("WARNING: new_node_id_list is empty")
      remaining_cycles = end_cycles

  if cycle_delete:
    url = fomg_url + "/127.0.0.1/5003/nodes"
    print_flush("DELETE", url)
    r = requests.delete(url, auth=(fomg_user, fomg_password), verify=False)

    time.sleep(1)

  remaining_cycles -= 1
  
  print_flush("Sleep for 2 minutes")
  time.sleep(120)

if test_delete:
  for node_id in test_node_id_list:
    # e.g. https://137.204.57.80:51117/fgw/10313/5005/test
    url = fgw_url + "/" + node_id + "/5005/test"
    print_flush("DELETE", url)
    r = requests.delete(url, auth=(fomg_user, fomg_password), verify=False)
    time.sleep(1)

if post_delete:
  url = fomg_url + "/127.0.0.1/5003/nodes"
  print_flush("DELETE", url)
  r = requests.delete(url, auth=(fomg_user, fomg_password), verify=False)
  time.sleep(1)

# get measurements
url = fomg_url + "/127.0.0.1/5003/meas"
print_flush("GET", url)
r = requests.get(url, auth=(fomg_user, fomg_password), verify=False)
#print_flush(json.dumps(meas_dict, indent=2))

with open(output_fname, "w") as f:
  json.dump(r.json(), f)

print_flush("Measurement data written to file {}".format(output_fname))

