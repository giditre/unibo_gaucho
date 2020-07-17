import matplotlib.pyplot as plt
import numpy as np

import argparse
import json

plt.rcdefaults()
plt.rcParams['font.size'] = 12
fig, ax = plt.subplots()
fig.tight_layout()

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

rects = ax.barh(y_pos[:2], [call_duration[c] for c in calls[:2]],
  left=[call_start[c] for c in calls[:2]], height = 0.5,
  linewidth=3, color="w", edgecolor="k", hatch="/")

rects += ax.barh(y_pos[2], [call_duration[c] for c in calls[2:]],
  left=[call_start[c] for c in calls[2:]], height = 0.5,
  linewidth=3, color="w", edgecolor="k", hatch="/")

ax.set_xlabel('Time [ms]')

ax.set_yticks([])
#ax.set_yticklabels(calls_short)
ax.invert_yaxis()  # labels read top-to-bottom

for i in range(len(calls)):
  c = calls[i]
  rect = rects[i]
  ax.annotate('{}'.format(calls_short[i]),
    xy=(call_start[c] + call_duration[c]/2, rect.get_y() + rect.get_height()),
    xytext=(0,-3), textcoords="offset points",
    ha='center', va='top')

plt.xlim((0, call_duration[calls[0]]))

ax.spines["bottom"].set_linewidth(1.5)

ax.spines["left"].set_linestyle("--")
ax.spines["left"].set_linewidth(1.5)

ax.spines["right"].set_position(("data", call_duration[calls[0]]))
ax.spines["right"].set_linestyle("--")
ax.spines["right"].set_linewidth(1.5)

ax.spines["top"].set_visible(False)

#def autolabel(rects):
#  """Attach a text label above each bar in *rects*, displaying its height."""
#  for i in range(len(rects)):
#    rect = rects[i]
#    width = rect.get_width()
#    ax.annotate('{}'.format(calls_short[i]),
#      xy=(rect.get_x(), rect.get_y() + rect.get_height() / 2),
#      textcoords="offset points",
#      ha='center', va='bottom')
#
#autolabel(rect)

plt.show()
