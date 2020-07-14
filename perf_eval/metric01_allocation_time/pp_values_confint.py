#!/usr/bin/python3

from sys import stdin
import numpy as np
import scipy as sp
import scipy.stats
import json
import argparse

def mean_std_confidence_interval(data, confidence=0.95):
  a = 1.0 * np.array(data)
  n = len(a)
  m, sd, se = np.mean(a), np.std(a), scipy.stats.sem(a)
  h = se * sp.stats.t._ppf((1 + confidence) / 2., n - 1)
  return m, m - h, m + h, sd

parser = argparse.ArgumentParser()

parser.add_argument("data_fname", help="Filename with input data")
parser.add_argument("-o", "--output-fname", help="Filename of post processed data", nargs="?", default=None)

args = parser.parse_args()
print("CLI args: {}".format(vars(args)))

data_fname = args.data_fname

output_fname = args.output_fname if args.output_fname else "pp_" + data_fname

with open(data_fname) as f:
  data = json.load(f)

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

