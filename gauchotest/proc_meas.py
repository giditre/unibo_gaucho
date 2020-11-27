import json
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

with open("get_meas_test_20200228_004941.json") as f:
  meas_dict = json.load(f)


sorted_t = sorted(meas_dict.keys())

sorted_host_id = sorted(meas_dict[sorted_t[0]].keys())
n_hosts = len(sorted_host_id)

plot_dict = { h: [] for h in sorted_host_id }

for t in sorted_t:
  meas = meas_dict[t]
  for host_id in sorted_host_id:
    item_dict = meas[host_id]
    for item_id in item_dict:
      item = item_dict[item_id]
      if item["name"] == "CPU utilization":
        #print(t, host_id, item["lastvalue"])
        plot_dict[host_id].append(round(float(item["lastvalue"])))

labels = [ str(int(t)-int(sorted_t[0])) for t in sorted_t ]

print(labels)
for h_id in plot_dict:
  print(plot_dict[h_id])

x = np.arange(len(labels))  # the label locations
width = 0.9/n_hosts  # the width of the bars

fig, ax = plt.subplots()

if n_hosts == 1:
  rect_list = [ ax.bar(x, plot_dict[sorted_host_id[0]], width, label=sorted_host_id[0]) ]
else:
  rect_list = [ ax.bar(x - width/2 + i*width/(n_hosts-1), plot_dict[sorted_host_id[i]], width, label=sorted_host_id[i]) for i in range(n_hosts) ]

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_title('CPU utilization')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel('CPU util.')
ax.set_ylim([0, 100])
ax.legend()


def autolabel(rects):
  """Attach a text label above each bar in *rects*, displaying its height."""
  for rect in rects:
    height = rect.get_height()
    ax.annotate('{}'.format(height),
      xy=(rect.get_x() + rect.get_width() / 2, height),
      xytext=(0, 3),  # 3 points vertical offset
      textcoords="offset points",
      ha='center', va='bottom')

for rect in rect_list:
  autolabel(rect)

fig.tight_layout()

plt.show()


