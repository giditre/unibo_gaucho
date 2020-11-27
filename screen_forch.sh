#!/bin/bash

screen -dmS forch bash -c 'cd; bash'
screen -S forch -X chdir

screen -S forch -X screen -t UA bash -c 'cd /home/gaucho/unibo_gaucho; bash'
screen -S forch -p UA -X stuff "python3 forch_user_access.py 0.0.0.0 5001"

screen -S forch -X screen -t BR bash -c 'cd /home/gaucho/unibo_gaucho; bash'
screen -S forch -p BR -X stuff "python3 forch_broker.py 0.0.0.0 5002"

screen -S forch -X screen -t RD bash -c 'cd /home/gaucho/unibo_gaucho; bash'
screen -S forch -p RD -X stuff "python3 forch_rsdb.py 0.0.0.0 5003"

screen -S forch -X screen -t IM bash -c 'cd /home/gaucho/unibo_gaucho; bash'
screen -S forch -p IM -X stuff "python3 forch_iaas_mgmt.py 0.0.0.0 5004"

screen -S forch -X screen -t top bash -c 'top; bash'

screen -r forch
