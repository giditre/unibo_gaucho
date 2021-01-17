# FROM giditre/ubuntu_slp_base:latest
# RUN pip3 install py-zabbix netifaces
# RUN apt-get install nano

FROM giditre/ubuntu_slp_base:zabbix_netifaces_nano

RUN mkdir -p /home/gaucho/mario
WORKDIR /home/gaucho/mario
RUN git clone https://github.com/mrv96/unibo_gaucho.git

# copy everything present in the Dockerfile directory into the container
# WORKDIR /home/gaucho/mario/unibo_gaucho/pyforch/src/forch
WORKDIR /home/gaucho/mario/unibo_gaucho/pyforch/tests/eval_tests/
CMD [ "python3", "./search_srv_eval_main.py", "n", "-i", "eth0", "-j", "./srvcs_1.json"]
