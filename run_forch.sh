#!/bin/bash

# function called by trap
cleanup() {
  echo -e "\nCleaning up..."
  cat /tmp/forch.pid | while read line; do
    pid="$(echo $line | cut -d" " -f1)"
    kill "$pid"
  done
  echo "Done."
  exit 0
}

trap 'cleanup' SIGINT

python3 forch_user_access.py 0.0.0.0 5001 & echo "$! forch_user_access.py 0.0.0.0 5001" > /tmp/forch.pid
python3 forch_broker.py 127.0.0.1 5002 & echo "$! forch_broker.py 127.0.0.1 5002"  >> /tmp/forch.pid
python3 forch_rsdb.py 127.0.0.1 5003 & echo "$! forch_rsdb.py 127.0.0.1 5003" >> /tmp/forch.pid
python3 forch_iaas_mgmt.py 127.0.0.1 5004 & echo "$! forch_iaas_mgmt.py 127.0.0.1 5004" >> /tmp/forch.pid

sleep 3

# check the expected processes are running on the expected ports
cat /tmp/forch.pid | while read line; do
  pid="$(echo $line | cut -d" " -f1)"
  module="$(echo $line | cut -d" " -f2)"
  port="$(echo $line | cut -d" " -f4)"
  [[ "$(lsof -ti :$port)" != "$pid" ]] && echo "PID mismatch for module $module" && exit 1
done

echo "FORCH is running - stop with Ctrl+C"

while true; do sleep 1; done

