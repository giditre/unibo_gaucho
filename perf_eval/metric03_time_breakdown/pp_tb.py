#!/usr/bin/python3

import sys
import numpy as np
import scipy as sp
import scipy.stats
import json
import argparse

import time
import datetime

import re

def mean_std_confidence_interval(data, confidence=0.95):
  a = 1.0 * np.array(data)
  n = len(a)
  m, sd, se = np.mean(a), np.std(a), scipy.stats.sem(a)
  h = se * sp.stats.t._ppf((1 + confidence) / 2., n - 1)
  return m, m - h, m + h, sd

parser = argparse.ArgumentParser()

parser.add_argument("data_fname", help="Filename with input data")

args = parser.parse_args()
print("CLI args: {}".format(vars(args)))

data_fname = args.data_fname

output_fname = data_fname.replace(".log", "_pp.json")

# TODO get from argument
user_call = "forch_user_access.py " + "POST /app/APP002"

data_list = []

with open(data_fname) as f:

  for line in f:

    # only consider lines with a marker
    if "marker" in line:
      print(line.strip())

      # extract timestamp
      m = re.search("\d+-\d+-\d+ \d+:\d+:\d+,\d+", line)
      if m:
        #print(m.group())
        ts_str = m.group()
        print(ts_str)
        ts_int = int(datetime.datetime.strptime(ts_str + "000", "%Y-%m-%d %H:%M:%S,%f").timestamp()*1000)
      else:
        print("WARNING: no timestamp found in line:\n{}\n".format(line))
        continue

      # extract module name
      m = re.search("forch.*\.py", line)
      if m:
        module_name = m.group()
        print(module_name)
      else:
        print("WARNING: no module name found in line:\n{}\n".format(line))
        continue

      if "start" in line:
        rest_call = module_name + " " + line.split("start")[1].strip()
        print(rest_call)
        if rest_call == user_call:
          entry = {
            "seq": [rest_call],
            "start": {
              rest_call: ts_int
            },
            "end": {}
          }
        else:
          entry["seq"].append(rest_call)
          entry["start"][rest_call] = ts_int

      elif "end" in line:
        rest_call = module_name + " " + line.split("end")[1].strip()
        print(rest_call)
        entry["end"][rest_call] = ts_int
        if rest_call == user_call:
          entry["elaps"] = {
            call: entry["end"][call] - entry["start"][call] for call in entry["seq"]
          }
          data_list.append(entry)
          print(entry)
        
      else:
        print("WARNING: no start/end indicator found in line:\n{}\n".format(line))
        continue

print(len(data_list))
print(json.dumps(data_list, indent=2)) 

typ_entry = None
for entry in data_list:
  if entry["elaps"][user_call] == 10237:
    typ_entry = entry
    break

if typ_entry:
  print("Typical entry found")

  t_start = typ_entry["start"][user_call]
  for rest_call in typ_entry["seq"]:
    typ_entry["start"][rest_call] -= t_start
    typ_entry["end"][rest_call] -= t_start
  
  print(json.dumps(typ_entry, indent=2))
  
  output_fname = data_fname.replace(".log", "_typ.json")
  
  with open(output_fname, "w") as f:
    json.dump(typ_entry, f)

sys.exit()

data_list = [
  entry for entry in data_list if entry["elaps"][user_call] > 150 and entry["elaps"][user_call] < 250
]

print(len(data_list))
print(json.dumps(data_list, indent=2)) 

# compute stats

elaps_dict = { rest_call: [] for rest_call in [
  "forch_user_access.py POST /app/APP002",
  "forch_broker.py GET /app/APP002",
  "forch_rsdb.py GET /nodes"
  ]
}

for entry in data_list:
  for rest_call in entry["seq"]:
    if rest_call in elaps_dict:
      elaps_dict[rest_call].append(entry["elaps"][rest_call])

print(json.dumps(elaps_dict, indent=2)) 

sys.exit()

values_list = data["values"]

mean, mean_low, mean_high, st_dev = mean_std_confidence_interval(values_list)

print("{:^10} {:^10} {:^10} {:^10}".format("Mean", "Mean low", "Mean high", "Std. Dev."))
print("{:^10.0f} {:^10.0f} {:^10.0f} {:^10.0f}".format(mean, mean_low, mean_high, st_dev))

pp_dict = {
  "mean": int(mean),
  "mean_high": int(mean_high),
  "mean_low": int(mean_low),
  "st_dev": int(st_dev)
}

with open(output_fname, "w") as f:
  json.dump(pp_dict, f)

