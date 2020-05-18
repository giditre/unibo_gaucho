#!/usr/bin/python3

import sys

import json
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

import argparse 

parser = argparse.ArgumentParser()

parser.add_argument("fname", help="File name")
parser.add_argument("-i", "--ignore-last", help="Number of trailing results to ignore, starting from most recent, default: 0", type=int, nargs="?", default=0)
parser.add_argument("-l", "--limit", help="Maximum number of results to show, starting from most recent, default: 1000", type=int, nargs="?", default=1000)
parser.add_argument("-f", "--fontsize", help="Font size, default: 10", type=int, nargs="?", default=10)
parser.add_argument("-w", "--widthfactor", help="Width factor, default: 0.9", type=float, nargs="?", default=0.9)
parser.add_argument("-s", "--figsizes", help="Sizes of the figure in inches, comma-separated values, default: 8,6", nargs="?", default="8,6")
parser.add_argument("-d", "--figdpi", help="DPI of the figure, default: 40", nargs="?", type=int, default=40)
parser.add_argument("--legend", help="Legend formatted as comma separated host_id:name (e.g., 10313:NUC1,10316:RP1), default: none [use host_id]", nargs="?", default="")
parser.add_argument("--show", help="Show plot, default: False", action="store_true", default=False)

args = parser.parse_args()
print("CLI args: {}".format(vars(args)))

fname = args.fname
ignore_last = args.ignore_last
limit = args.limit
fontsize = args.fontsize
width_factor = args.widthfactor
fig_width = int(args.figsizes.split(",")[0])
fig_height = int(args.figsizes.split(",")[1])
fig_dpi = args.figdpi
legend_str = args.legend
plt_show = args.show

# set font size
plt.rcParams.update({"font.size": fontsize})

with open(fname) as f:
  meas_dict = json.load(f)

sorted_t = sorted(meas_dict.keys())

# apply ignore_last
if ignore_last > 0:
  sorted_t = sorted_t[:-ignore_last]
# apply limit
if len(sorted_t) > limit:
  sorted_t = sorted_t[-limit:]

#  list and sort host_id and flter out those not included in the legend
host_id_list = []
for t in meas_dict:
  for h_id in meas_dict[t]:
    if h_id not in host_id_list:
      host_id_list.append(h_id)
sorted_host_id_list = sorted(host_id_list)
n_hosts = len(sorted_host_id_list)
print(n_hosts, sorted_host_id_list)

# process the legend
legend = {}
if legend_str:
  for pair in legend_str.split(","):
    h_id, name = pair.split(":")
    legend[h_id] = name
else:
  legend = { h_id:h_id for h_id in sorted_host_id_list }
print("legend", legend)

sorted_host_id_list = [ h_id for h_id in sorted_host_id_list if h_id in legend ]

patterns = [ "//", "\\", "+", "x", "|", "/", "-", ".", "o", "O", "*" ]

plot_dict = { h: {} for h in sorted_host_id_list }

lastclock_dict = {}

for t in sorted_t:
  meas = meas_dict[t]
  for host_id in sorted_host_id_list:
    item_dict = meas[host_id]
    lastclock_dict[host_id] = 0
    is_available = False
    for item_id in item_dict:
      item = item_dict[item_id]
      if item["name"] == "available":
        if item["lastvalue"] == "1":
          is_available = True
        break
    for item_id in item_dict:
      item = item_dict[item_id]
      if item["name"] == "CPU utilization":
        #print(t, host_id, item["lastvalue"])
        if item["lastclock"] != lastclock_dict[host_id]:
          lastclock_dict[host_id] = item["lastclock"]
          if is_available:
            plot_dict[host_id][item["lastclock"]] = round(float(item["lastvalue"]))
          else:
            plot_dict[host_id][item["lastclock"]] = 0

# trim length of plot_dict
min_length = min( [ len(plot_dict[h_id]) for h_id in plot_dict ] )
for h_id in plot_dict:
  while len(plot_dict[h_id]) > min_length:
    last_t = max(plot_dict[h_id].keys())
    del plot_dict[h_id][last_t]

# create x axis labels
labels = [ str(t) for t in range(min_length) ]

# display information
print("labels", len(labels), labels)
for h_id in plot_dict:
  print("h_id", h_id)
  print("plot_dict", plot_dict[h_id])
  print("plot_dict keys", len(plot_dict[h_id].keys()), plot_dict[h_id].keys())
  print("plot_dict values", len(plot_dict[h_id].values()), plot_dict[h_id].values())

x = np.arange(len(labels))  # the label locations
width = width_factor/n_hosts  # the width of the bars

fig, ax = plt.subplots()

#if n_hosts == 1:
#  rect_list = [ ax.bar(x, plot_dict[sorted_host_id_list[0]], width, label=sorted_host_id_list[0]) ]
#else:
#  rect_list = [ ax.bar(x - (n_hosts-1)/2 * width + i*width, plot_dict[sorted_host_id_list[i]], width, label=sorted_host_id_list[i]) for i in range(n_hosts) ]

rect_list = [ ax.bar( np.arange(len(plot_dict[sorted_host_id_list[i]].values())) - (n_hosts-1)/2 * width + i*width, list(plot_dict[sorted_host_id_list[i]].values()), width, label=legend[sorted_host_id_list[i]], hatch=patterns[i], alpha=.99) for i in range(n_hosts) ]

# Add some text for labels, title and custom x-axis tick labels, etc.
#ax.set_title("CPU utilization")
ax.set_xlabel("Time [min]")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("CPU utilization [%]")
ax.set_ylim([0, 120])
ax.legend()


#def autolabel(rects):
#  """Attach a text label above each bar in *rects*, displaying its height."""
#  for rect in rects:
#    height = rect.get_height()
#    ax.annotate('{}'.format(height),
#      xy=(rect.get_x() + rect.get_width() / 2, height),
#      xytext=(0, 3),  # 3 points vertical offset
#      textcoords="offset points",
#      ha='center', va='bottom')

#for rect in rect_list:
#  autolabel(rect)

fig.tight_layout()
#plt.margins(0)

fig.set_size_inches(fig_width, fig_height)
fig.set_dpi(fig_dpi)

if plt_show:
  plt.show()

plt.savefig('out.pdf', bbox_inches='tight')

