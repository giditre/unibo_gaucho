#!/bin/bash

screen -dmS forchdev bash -c 'cd; bash'
screen -S forchdev -X 'chdir'

screen -S forchdev -X screen -t UA bash -c 'cd /home/gaucho/unibo_gaucho; bash'
screen -S forchdev -p UA -X stuff "vim forch_user_access.py"

screen -S forchdev -X screen -t BR bash -c 'cd /home/gaucho/unibo_gaucho; bash'
screen -S forchdev -p BR -X stuff "vim forch_broker.py"

screen -S forchdev -X screen -t RD bash -c 'cd /home/gaucho/unibo_gaucho; bash'
screen -S forchdev -p RD -X stuff "vim forch_rsdb.py"

screen -S forchdev -X screen -t IM bash -c 'cd /home/gaucho/unibo_gaucho; bash'
screen -S forchdev -p IM -X stuff "vim forch_iaas_mgmt.py"

screen -S forchdev -X screen -t git bash -c 'cd /home/gaucho/unibo_gaucho; bash'
screen -S forchdev -p git -X stuff 'git pull && git add -A && git commit -a -m "commit from $(hostname) on $(date)" && git push^M'

screen -r forch
