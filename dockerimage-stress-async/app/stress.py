from typing import Optional, List

import time
import json
import subprocess
import argparse

# def stress_routine(timeout: int) -> None:
#   end_t = time.time() + timeout
#   print(f"Stress routine {current_process().name} ends in {timeout} seconds.")
#   try:
#     while True:
#       if time.time() > end_t:
#         break
#       end_t*end_t # could be any pair of numbers - we're multiplying them only to load CPU
#       print(f"Stress routine {current_process().name} has ended.")
#   except KeyboardInterrupt:
#     pass

def stress_main(*, file_name, check_interval):

  print(f"stress_main, check_interval {check_interval}")

  while True:

    try:
      with open(file_name) as f:
        stress_json = json.load(f)
    except:
      print("Error while accessing file.")
      time.sleep(check_interval)
      continue

    end_t = int(stress_json["end_t"])

    if time.time() < end_t:
      cmd = f"stress-ng --timeout {check_interval}"
      for k, v in stress_json["args"].items():
        if k != "timeout":
          cmd += f" --{k} {v}"
      print(cmd)
      subprocess.run(cmd.split()) # this is blocking
    else:
      time.sleep(check_interval)

if __name__ == "__main__":

  default_file_name = "/app/stress.json"
  default_interval = 10

  parser = argparse.ArgumentParser()
  
  parser.add_argument("-f", "--file-name", help=f"File name, default: {default_file_name}", nargs="?", default=default_file_name)
  parser.add_argument("-i", "--interval", help=f"File check interval, default: {default_interval}", type=int, nargs="?", default=default_interval)

  args = parser.parse_args()

  print("CLI args: {}".format(vars(args)))
  
  stress_main(file_name=args.file_name, check_interval=args.interval)