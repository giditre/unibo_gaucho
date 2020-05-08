#!/bin/bash

service=""
while getopts 'ips' OPTION ; do
  case $OPTION in
    i) service="iaas"
    ;;
    p) service="paas"
    ;;
    s) service="saas"
    ;;
    ?) echo "Unknown parameter $OPTION"
       exit 1
    ;;
  esac
done
shift $(($OPTIND-1))

# function called by trap
cleanup() {
  echo -e "\nCleaning up..."
  cat /tmp/fnode.pid | while read line; do
    pid="$(echo $line | cut -d" " -f1)"
    kill "$pid"
  done
  echo "Done."
  exit 0
}

trap 'cleanup' SIGINT

python3 fnode_$service.py 0.0.0.0 5005 & echo "$! fnode_$service.py 0.0.0.0 5005" > /tmp/fnode.pid

sleep 3

# check the expected processes are running on the expected ports
cat /tmp/fnode.pid | while read line; do
  pid="$(echo $line | cut -d" " -f1)"
  module="$(echo $line | cut -d" " -f2)"
  port="$(echo $line | cut -d" " -f4)"
  [[ "$(lsof -ti :$port)" != "$pid" ]] && echo "PID mismatch for module $module" && exit 1
done

echo "Fog Node $service is running - stop with Ctrl+C"

while true; do sleep 1; done

