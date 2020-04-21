curl -X DELETE http://127.0.0.1:5003/nodes
curl http://192.168.10.117:5001/apps
while [[ "$(curl --write-out %{http_code} http://192.168.10.117:5001/app/APP002 2>/dev/null | tee -a ../gauchotest/allocation_test.log | tee /tmp/last_allocation_test.log | tail -1)" == 20* ]] ; do
  cat /tmp/last_allocation_test.log
  echo
  sleep 120
done
sleep 240
curl http://127.0.0.1:5003/meas 2>/dev/null > ../gauchotest/get_meas_test_$(date +"%Y%m%d_%H%M%S").json
curl -X DELETE http://127.0.0.1:5003/nodes
