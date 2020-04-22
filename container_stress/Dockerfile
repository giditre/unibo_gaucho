FROM alpine:latest

RUN apk update
RUN apk add python3 python3-dev stress-ng
RUN pip3 install --upgrade pip

WORKDIR /usr/bin
RUN ln -s stress-ng stress

WORKDIR /root

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY fnode_app_stress.py .
COPY run.sh .

EXPOSE 5100

#ENTRYPOINT exec screen -S fnodetest -dm sh -c python3 fnode_saas.py 0.0.0.0 5100
#ENTRYPOINT exec screen -S test -dm sh

#/usr/bin/screen -S fnodetest -m /bin/sh -c /usr/bin/python3 /root/fnode_saas.py 0.0.0.0 5100

#ENTRYPOINT /bin/sh
#CMD ["-c", "/usr/bin/screen", "-S", "fnodetest", "-dm", "/bin/sh", "-c", "\"/usr/bin/python3", "/root/fnode_saas.py", "0.0.0.0", "5100\""]

CMD ["/root/run.sh"]
