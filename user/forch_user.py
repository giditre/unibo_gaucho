import requests
import json
import sys
import argparse
import time

### Command line argument parser

default_endpoint = "127.0.0.1:6000"
default_path = "services"
default_method = "GET"
default_project = "default"

parser = argparse.ArgumentParser()
parser.add_argument("--endpoint", help=f"FO endpoint, default: {default_endpoint}", nargs="?", default=default_endpoint)
parser.add_argument("--path", help=f"FO path, default: {default_path}", nargs="?", default=default_path)
parser.add_argument("--method", help=f"FO method, default: {default_method}", nargs="?", default=default_method)
parser.add_argument("--project", help=f"FO project, default: {default_project}", nargs="?", default=default_project)
parser.add_argument("--measure-time", help="Measure response time", action="store_true", default=False)
parser.add_argument("-y", "--assume-yes", help="Automatic yes to prompts", action="store_true", default=False)
args = parser.parse_args()

print("CLI args: {}".format(json.dumps(vars(args), indent=2)))

if not args.assume_yes:
  c = input("Confirm? [y/n] ")
  if c != "y":
    sys.exit("Aborted.")

# compose request URL based on endpoint and path
url = f"http://{args.endpoint}/{args.path}"
print(f"Request URL: {url}")

# initialize response and start time (both useful for measuring response time)
response = None
t_start = time.time()

if args.method == "GET":
  # send request
  response = requests.get(url)
  response_json = response.json()
  print(f"Response JSON: {json.dumps(response_json, indent=2)}")

elif args.method == "PUT":
  pass

elif args.method == "POST":
  request_json = {"project": args.project}
  print(f"Request JSON: {json.dumps(request_json, indent=2)}")
  # send request
  response = requests.post(url, json=request_json)
  response_json = response.json()
  print(f"Response JSON: {json.dumps(response_json, indent=2)}")
  if response.status_code not in [200, 201]:
    sys.exit(f"Code {response.status_code}")

elif args.method == "DELETE":
  # send request
  response = requests.delete(url)
  response_json = response.json()
  print(f"Response JSON: {json.dumps(response_json, indent=2)}")

else:
  raise NotImplementedError

# mark end time
t_end = time.time()

if response is not None:
  print(f"Response header time: {response.elapsed.total_seconds():.3f} s")

  clock_time = t_end-t_start
  print(f"Response total time: {clock_time:.3f} s")