import matplotlib.pyplot as plt
import numpy as np

import argparse
import json

plt.rcdefaults()
fig, ax = plt.subplots()

parser = argparse.ArgumentParser()

parser.add_argument("fname", help="File name")
# parser.add_argument("-i", "--ignore-last", help="Number of trailing results to ignore, starting from most recent, default: 0", type=int, nargs="?", default=0)
# parser.add_argument("--show", help="Show plot, default: False", action="store_true", default=False)

args = parser.parse_args()
print("CLI args: {}".format(vars(args)))

fname = args.fname

# gather data
with open(fname) as f:
  data_dict = json.load(f)

calls = data_dict["seq"]

print("calls", calls)

module_short_name_dict = {
  "forch_user_access.py": "UA",
  "forch_broker.py": "BR",
  "forch_rsdb.py": "RD",
  "forch_iaas_mgmt.py": "IM"
}

calls_short = []
for c in calls:
  for mn, msn in module_short_name_dict.items():
    if mn in c:
      calls_short.append(c.replace(mn, msn))
print("calls_short", calls_short)

y_pos = np.arange(len(calls))

call_duration = { call: data_dict["elaps"][call] for call in calls }
print("call_duration", call_duration)

call_start = { call: data_dict["start"][call] for call in calls }
print("call_start", call_start)

ax.barh(y_pos, [call_duration[c] for c in calls], left=[call_start[c] for c in calls], color="w", edgecolor="k")
ax.set_yticks(y_pos)
ax.set_yticklabels(calls_short)
ax.invert_yaxis()  # labels read top-to-bottom
ax.set_xlabel('Time [ms]')

plt.show()
