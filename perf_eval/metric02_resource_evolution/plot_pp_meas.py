#!/usr/bin/python3

import sys

import json
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

import argparse 

###

n_cpu = {
  "10313": 8,
  "10314": 2,
  "10315": 2,
  "10316": 4,
  "10317": 2,
  "10318": 2
}

###

parser = argparse.ArgumentParser()

parser.add_argument("fname", help="File name")
parser.add_argument("-i", "--ignore-last", help="Number of trailing results to ignore, starting from most recent, default: 0", type=int, nargs="?", default=0)
parser.add_argument("-l", "--last-minutes", help="Only show the last l minutes, default: 0", type=int, nargs="?", default=0)
parser.add_argument("-f", "--fontsize", help="Font size, default: 10", type=int, nargs="?", default=10)
parser.add_argument("-w", "--widthfactor", help="Width factor, default: 0.5", type=float, nargs="?", default=0.5)
parser.add_argument("-s", "--figsizes", help="Sizes of the figure in inches, comma-separated values, default: 8,6", nargs="?", default="8,6")
parser.add_argument("-d", "--figdpi", help="DPI of the figure, default: 40", nargs="?", type=int, default=40)
parser.add_argument("--legend", help="Legend formatted as comma separated host_id:name (e.g., 10313:NUC1,10316:RP1), default: none [use host_id]", nargs="?", default="")
parser.add_argument("--show", help="Show plot, default: False", action="store_true", default=False)

args = parser.parse_args()
print("CLI args: {}".format(vars(args)))

fname = args.fname
ignore_last = args.ignore_last
last_minutes = args.last_minutes
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
  pp_dict = json.load(f)

#plot_dict = {
#  node_id: [ round(n_cpu[node_id]*value/100.0, 2) for value in pp_dict[node_id] ] for node_id in pp_dict
#}

node_id_list = list(pp_dict.keys())
print("node_id_list", node_id_list)

# process the legend
legend = {}
if legend_str:
  for pair in legend_str.split(","):
    h_id, name = pair.split(":")
    legend[h_id] = name
else:
  legend = { h_id:h_id for h_id in node_id_list }
print("legend", legend)

node_id_list = [ node_id for node_id in node_id_list if node_id in legend ]
print("node_id_list", node_id_list)

N = len(pp_dict[node_id_list[0]])
print("N", N)

# last minutes
N_start = N-last_minutes if last_minutes > 0 else 0
print("N_start", N_start)

plot_dict = {}
tot_cpu = [0] * N

for node_id in node_id_list:
  plot_dict[node_id] = []
  for i in range(N_start, N):
    value = pp_dict[node_id][i]
    if value >= 0:
      plot_dict[node_id].append(round(n_cpu[node_id]*value/100.0, 2))
      #print(i, node_id)
      tot_cpu[i] += n_cpu[node_id]
    else:
      plot_dict[node_id].append(0)

tot_cpu = tot_cpu[-last_minutes:]

print("plot_dict", len(plot_dict[node_id_list[0]]), json.dumps(plot_dict))
print("tot_cpu", len(tot_cpu), tot_cpu)

width = width_factor
ind = np.arange(len(tot_cpu))

plot_handle_dict = {
  "0": plt.bar(ind, tot_cpu, width, color="w", edgecolor="k", label="Total CPUs")
}

plot_handle_dict[node_id_list[0]] = plt.bar(ind, plot_dict[node_id_list[0]], width, label=legend[node_id_list[0]])

bottom_values = [0] * len(tot_cpu)

for i in range(1, len(node_id_list)):
  prev_node_id = node_id_list[i-1]
  bottom_values = [ sum(x) for x in zip(bottom_values, plot_dict[prev_node_id]) ]
  node_id = node_id_list[i]
  plot_handle_dict[node_id] = plt.bar(ind, plot_dict[node_id], width, bottom=bottom_values, label=legend[node_id])

plt.xlabel('Time [min]')
plt.ylabel('Number of CPUs')
plt.legend()

plt.show()

