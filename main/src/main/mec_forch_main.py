import requests
import json
import sys

if __name__ == '__main__':

  ### Command line argument parser

  default_endpoint = "127.0.0.1:6000"
  default_path = "services"
  default_method = "GET"
  default_project = "default"
  default_hosts_file = None
  # default_hosts_format = ""
  default_hosts_domain = None

  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("--endpoint", help=f"FO endpoint, default: {default_endpoint}", nargs="?", default=default_endpoint)
  parser.add_argument("--path", help=f"FO path, default: {default_path}", nargs="?", default=default_path)
  parser.add_argument("--method", help=f"FO method, default: {default_method}", nargs="?", default=default_method)
  parser.add_argument("--project", help=f"FO project, default: {default_project}", nargs="?", default=default_project)
  parser.add_argument("--overwrite-hosts", help="Overwrite hosts", action="store_true", default=False)
  parser.add_argument("--hosts-file", help=f"FO hosts file, default: {default_hosts_file}", nargs="?", default=default_hosts_file)
  # parser.add_argument("--hosts-format", help=f"FO hosts format, default: {default_hosts_file}", nargs="?", default=default_hosts_file)
  parser.add_argument("--hosts-domain", help=f"FO hosts domain, default: {default_hosts_domain}", nargs="?", default=default_hosts_domain)
  parser.add_argument("-y", "--assume-yes", help="Automatic yes to prompts", action="store_true", default=False)
  args = parser.parse_args()

  print("CLI args: {}".format(json.dumps(vars(args), indent=2)))

  if not args.assume_yes:
    c = input("Confirm? [y/n] ")
    if c != "y":
      sys.exit("Aborted.")

  url = f"http://{args.endpoint}/{args.path}"

  if args.method == "GET":

    response = requests.get(url)

    response_json = response.json()

    print(f"Response: {json.dumps(response_json, indent=2)}")

  elif args.method == "PUT":
    pass

  elif args.method == "POST":

    response = requests.post(url, json={"project":args.project})

    response_json = response.json()

    print(f"Response: {json.dumps(response_json, indent=2)}")

    if response.status_code not in [200, 201]:
      sys.exit(f"Code {response.status_code}")

    # TODO relegate this to function that also checks uniqueness of IP
    if args.hosts_file:
      # increment serial number
      lines = []
      with open(args.hosts_file) as f:
        lines = f.readlines()
      for i in range(len(lines)):
        l = lines[i]
        # print(l)
        if "serial" in l:
          splitted_l = l.split()
          # print(splitted_l)
          for j in range(len(splitted_l)):
            e = splitted_l[j]
            # print(e)
            if e.isdigit():
              splitted_l[j] = str(int(e)+1)
              new_l = " ".join(["\t"] + splitted_l + ["\n"])
              # print(new_l)
              lines[i] = new_l
              break
          with open(args.hosts_file, "w") as f:
            f.writelines(lines)
          break
      
      with open(args.hosts_file, "a") as f:
        f.write(f'{response_json["instance_name"]} 60 IN A {response_json["instance_ip"]}\n') # TODO parametrize format
        # if args.hosts_domain:
        #   f.write(f".{args.hosts_domain}")
        # f.write("\n")

  elif args.method == "DELETE":

    response = requests.delete(url)

    response_json = response.json()

    print(f"Response: {json.dumps(response_json, indent=2)}")

  else:
    raise NotImplementedError