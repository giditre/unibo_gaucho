#!/bin/bash

python3 forch_user_access.py 0.0.0.0 5001
python3 forch_broker.py 127.0.0.1 5002
python3 forch_rsdb.py 127.0.0.1 5003
python3 forch_iaas_mgmt.py 127.0.0.1 5004

