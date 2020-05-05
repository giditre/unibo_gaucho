#!/bin/bash

#infname=$1

#data="[$(cat - | grep -v -e "^#" | grep -e "." | while read value; do echo "$value,"; done | sed 's/\n//g')]"

#echo $data
#exit 1

cat - | grep -v -e "^#" | grep -e "." | python3.6 <(
cat <<-EOF
from sys import stdin
import numpy as np
import scipy as sp
import scipy.stats

def mean_std_confidence_interval(data, confidence=0.95):
  a = 1.0 * np.array(data)
  n = len(a)
  m, sd, se = np.mean(a), np.std(a), scipy.stats.sem(a)
  h = se * sp.stats.t._ppf((1 + confidence) / 2., n - 1)
  return m, m - h, m + h, sd

#print(stdin.readlines())

data = [ float(value.replace('\n', '')) for value in stdin.readlines()]

#print(data)

mean, mean_low, mean_high, st_dev = mean_std_confidence_interval(data)

print(mean, mean_low, mean_high, st_dev)

EOF
) | awk '{ printf "# mean %15.3f mean_low %15.3f mean_high %15.3f st_dev %15.3f\n",$1,$2,$3,$4 }'
