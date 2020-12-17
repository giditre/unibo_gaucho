import requests
import json
import sys

if __name__ == '__main__':

  ### Command line argument parser

  default_endpoint = "127.0.0.1:6000"
  default_path = "services"
  default_method = "GET"
  default_project = "default"
  default_hostsfile = ""

  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("--endpoint", help=f"FO endpoint, default: {default_endpoint}", nargs="?", default=default_endpoint)
  parser.add_argument("--path", help=f"FO path, default: {default_path}", nargs="?", default=default_path)
  parser.add_argument("--method", help=f"FO method, default: {default_method}", nargs="?", default=default_method)
  parser.add_argument("--project", help=f"FO project, default: {default_project}", nargs="?", default=default_project)
  parser.add_argument("--foghostsfile", help=f"FO hosts file, default: {default_hostsfile}", nargs="?", default=default_hostsfile)
  parser.add_argument("-y", "--assume-yes", help="Automatic yes to prompts", action="store_true", default=False)
  args = parser.parse_args()

  print("CLI args: {}".format(json.dumps(vars(args), indent=2)))

  if not args.assume_yes:
    c = input("Confirm? [y/n] ")
    if c != "y":
      sys.exit("Aborted.")

  url = f"http://{args.endpoint}/{args.path}"

  if args.method == "GET":
    pass

  elif args.method == "PUT":
    pass

  elif args.method == "POST":

    response = requests.post(url, json={"project":args.project})

    response_json = response.json()

    print(f"Response: {json.dumps(response_json, indent=2)}")

    if args.foghostsfile:
      with open(args.foghostsfile, "a") as f:
        f.write(f'{response_json["instance_ip"]} {response_json["instance_name"]}\n')

  elif args.method == "DELETE":

    response = requests.delete(url)

    response_json = response.json()

    print(f"Response: {json.dumps(response_json, indent=2)}")

  else:
    raise NotImplementedError