FROM giditre/ubuntu_slp_base:latest

RUN cd /home
RUN git clone https://github.com/mrv96/unibo_gaucho

# copy everything present in the Dockerfile directory into the container
WORKDIR /home/unibo_gaucho/pyforch/tests/main_tests/
CMD [ "sudo python3 ./search_srv_eval_main.py", "o", "-j", "srvcs_1.json"]
