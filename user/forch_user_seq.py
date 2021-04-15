#echo "GET /services"
#python3 forch_user.py -y --method GET --path services
#echo "POST /services/APP002"
#python3 forch_user.py -y --method POST --path services/APP002
#echo "stress"
#curl -d '{"load":100,"timeout":180}' 192.168.64.118:8080/stress & echo $!
#echo "sleep 120"
#sleep 120
#echo "POST /services/APP002"
#python3 forch_user.py -y --method POST --path services/APP002

import sys
import requests
import time
import json

from typing import Dict

from forch_user import fu_parser, user_request, print_flush

# import urllib3
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def user_request_sequence(*, endpoint: str, path: str, method: str, project: str, service_data_json: Dict, n_cycles: int) -> None:

  urs_json = {
    "preliminary": [],
    "cycles": []
  }

  # # preliminary
  # url = f"http://{endpoint}"
  # print_flush("GET", url)
  # r = requests.get(url)
  # time.sleep(1)

  # url = f"http://{endpoint}/{path}"
  # print_flush("POST", url)
  # r = requests.post(url, json={"project":project})
  # time.sleep(1)

  # resp_json = r.json()
  # print_flush(json.dumps(resp_json, indent=2))

  for c in range(n_cycles):
    print_flush(f"Cycle {c}")

    urs_cycle_json = {
      "url": None,
      "method": None,
      "resp_json": None,
      "resp_code": None,
      "resp_time": None
    }

    url = f"http://{args.endpoint}/{args.path}"
    print_flush("POST", url)
    urs_cycle_json["method"] = "POST"
    urs_cycle_json["url"] = url

    response = user_request(url=url, method=method, project=project)
    urs_cycle_json["resp_code"] = response.status_code
    urs_cycle_json["resp_json"] = response.json()
    urs_cycle_json["resp_time"] = response.elapsed.total_seconds()
    urs_json["cycles"].append(urs_cycle_json)
    
    time.sleep(5)

    if response.status_code in [200, 201]:
      resp_json = response.json()
      node_ip = resp_json["node_ip"]
      node_port = resp_json["node_port"]
      url = f"http://{node_ip}:{node_port}/stress"
      print_flush("POST", url)
      response = requests.post(url, json=service_data_json)
      time.sleep(5)
      resp_json = response.json()
      print_flush(json.dumps(resp_json, indent=2))
      time.sleep(120)
    else:
      # response_code = response.status_code
      # print_flush(f"Response code: {response_code}")
      # response_json = response.json()
      # print_flush(f"Response JSON: {json.dumps(response_json, indent=2)}")
      break

  print_flush(json.dumps(urs_json))  


if __name__ == "__main__":

  ### Command line argument parser
  import argparse

  default_cycles = 10

  parser = fu_parser

  parser.add_argument("-d", "--service-data", help="Service data to be passed to the request starting the service, default: {}", nargs="?", default="{}")
  parser.add_argument("-n", "--num-cycles", help="Maximum number of measurement cycles", type=int, nargs="?", default=default_cycles)

  args = parser.parse_args()
  print_flush("CLI args: {}".format(vars(args)))

  if not args.assume_yes:
    c = input("Confirm? [y/n] ")
    if c != "y":
      sys.exit("Aborted.")

  user_request_sequence(endpoint=args.endpoint, path=args.path,
    method=args.method, project=args.project,
    service_data_json=json.loads(args.service_data), n_cycles=args.num_cycles)
