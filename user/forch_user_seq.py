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

import argparse
import sys

from forch_user import user_request

# import urllib3
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def print_flush(*args, **kwargs):
  kwargs["flush"] = True
  print(*args, **kwargs)

parser = argparse.ArgumentParser()

parser.add_argument("-n", "--num-cycles", help="Number of measurement cycles", type=int, nargs="?", default=100)

args = parser.parse_args()
print_flush("CLI args: {}".format(vars(args)))

if not args.assume_yes:
  c = input("Confirm? [y/n] ")
  if c != "y":
    sys.exit("Aborted.")