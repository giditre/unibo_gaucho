<img src="/FORCH_logo.png" width="150" align="right">

# UniBo GAUChO: FORCH

Introducing FORCH, a modular system for Fog Orchestrations container-based resorce allocation, developed in the context of project GAUChO by the team of the University of Bologna.

This PoC implementation is written in Python3. Its REST API is built using Flask RESTful, and it is for research and development purposes only, as it is not safe for production enviroments.

## Setting up the environment

It is suggested to operate inside of a [venv](https://docs.python.org/3.6/library/venv.html).

Make sure the following Python3 modules are installed:
```
flask_restful
requests
docker
pyzabbix
```
This can be also achieved by cloning the repo, then moving into the directory, and let pip3 do the work:
```
git clone giditre/unibo_gaucho
cd unibo_gaucho/
pip3 install -r requirements.txt
```

## Running FORCH

FORCH consists of multiple independent components, which may be run on the same machine or on separate machines, as the communication between them happens via REST calls. However, in the development phase, for security purposes it is suggested to run all of the FORCH components on a single machine and make all of them listen only on the loopback interface (127.0.0.1), except for the User Access component (_forch_user_api.py_) which is the only one using HTTPS (as opposed to the others using unencrypted HTTP).

From inside of the repo directory, run each of the components with
```
python3 <component_file_name> <IP_address> <TCP_port>
```
for example:
```
`python3 forch_user_api.py 0.0.0.0 5001`
```
or
```
python3 forch_broker.py 127.0.0.1 5002
```

The address 0.0.0.0 makes the components listen on all of the machine's interfaces, while 127.0.0.1 makes it listen only on the loopback interface.

The choice of the TCP port is arbitrary. However, by default the ports are mapped this way:
Component | Port
----------|-----
forch_user_api.py | 5001
forch_broker.py | 5002
forch_rsdb.py | 5003
forch_iaas_mgmt.py | 5004
fnode_saas.py / fnode_paas.py / fnode_iaas.py | 5005

Running a component with a customized port required the other components to be instructed on the choice. This can be achieved by specifying comman line arguments for every component detailing the choice of IP addresses and ports. For the list of available CLI arguments for every component and for their usage, refer to the inline help of each component, by running:
```
python3 <component_file_name> --help
```

### FORCH REST API

#### User Access (_forch_user_api.py_)

* Test

  * `GET /test`

    **Code:** 200 <br />
    **Sample content:**
    ```json
    {
      "message": "This endpoint is up!"
    }
    ```

* APPs

  * `GET /apps`
  
  **Code:** 200 <br />
  **Sample Content:**
  ```json
  {
    "APP001": {
      "name": "httpd",
      "descr": "Apache web server"
    },
    "APP002": {
      "name": "stress",
      "descr": "Stress host"
    }
  }
  ```
  
  * `GET /app/<app_id>`
  
  **Code:** 200 <br />
  **Sample Content:**
  ```json
  {
    "message": "App APP001 allocated",
    "node_class": "I",
    "node_id": "10313",
    "service_port": "32772"
  }
  ```
  
* SDPs

  * `GET /sdps`
  
  **Code:** 200 <br />
  **Sample Content:** 
  ```json
  {
    "SDP001": {
      "name": "python",
      "descr": "Python3"
    },
    "SDP002": {
      "name": "alpine",
      "descr": "Lightweight Ubuntu"
    }
  }
  ```
  
  * `GET /sdp/<sdp_id>`
  
  **Code:** 200 <br />
  **Sample Content:** 
  ```json
  {
    "message": "SDP SDP001 allocated",
    "node_class": "P",
    "node_id": "10315",
    "service_port": 35676
  }
  ```
  
* FVEs

  * `GET /fves`
  
  **Code:** 200 <br />
  **Sample Content:** 
  ```json
  {
    "FVE001": {
      "name": "docker",
      "descr": "Docker engine"
    }
  }
  ```
  
  * `GET /fve/<fve_id>`
  
  **Code:** 200 <br />
  **Sample Content:** 
  ```json
  {
    "message": "FVE FVE001 allocated",
    "node_class": "I",
    "node_id": "10313",
    "service_port": 37507
  }
  ```
  
* Fog Gateway to allocated services

  * `GET /fgw/<node_id>/<node_port>`
  
  * `POST /fgw/<node_id>/<node_port>`
  
  * `GET /fgw/<node_id>/<node_port>/<path>`
  
  * `POST /fgw/<node_id>/<node_port>/<path>`

#### Broker (_forch_broker.py_)
  Test, '/test'
  
  FogApplication, '/app/<app_id>'
  
  SoftDevPlatform, '/sdp/<sdp_id>'
  
  FogVirtEngine, '/fve/<fve_id>'

#### Resource Datababe (_forch_rsdb.py_)

  Test, '/test'
  
  FogNodeList, '/nodes'
  
  FogNode, '/node/<node_id>'
  
  FogMeasurements, '/meas'
  
  FogApplicationCatalog, '/appcat'
  
  FogApplicationList, '/apps'
  
  FogApplication, '/app/<app_id>'
  
  SoftDevPlatformCatalog, '/sdpcat'
  
  SoftDevPlatformList, '/sdps'
  
  SoftDevPlatform, '/sdp/<sdp_id>'
  
  FogVirtEngineCatalog, '/fvecat'
  
  FogVirtEngineList, '/fves'
  
  FogVirtEngine, '/fve/<fve_id>'

#### IaaS node management (_forch_iaas_mgmt.py_)

  Test, "/test"
  
  ImageList, "/images"
  
  FogApplication, "/app/<app_id>"
  
  SoftDevPlatform, "/sdp/<sdp_id>"
  
  FogVirtEngine, "/fve/<fve_id>"


### Fog Node management API

#### SaaS node management agent (_fnode_saas.py_)

  Test, '/test'
  
  FogNodeInfo, '/info'
  
  FogApplicationList, '/apps'
  
  FogApplication, '/app/<app_id>'
  
#### PaaS node management agent (_fnode_paas.py_)

  Test, '/test'
  
  FogNodeInfo, '/info'
  
  SoftDevPlatformList, '/sdps'
  
  SoftDevPlatform, '/sdp/<sdp_id>'

#### IaaS node management agent (_fnode_iaas.py_)

  Test, '/test'
  
  FogNodeInfo, "/info"
  
  FogApplicationList, '/apps'
  
  FogApplication, '/app/<app_id>'
  
  SoftDevPlatformList, '/sdps'
  
  SoftDevPlatform, '/sdp/<sdp_id>'
  
  FogVirtEngineList, '/fves'
  
  FogVirtEngine, '/fve/<fve_id>'

### Fog Node Service API

#### SaaS APP stress (_fnode_app_stress.py_)

  Test, '/test'
  
  FogNodeInfo, '/info'
  
  FogApplication, '/app/<app_id>'

#### PaaS SDP Python3 (_fnode_sdp_python.py_)

  Test, '/test'
  
  FogNodeInfo, '/info'
  
  SoftDevPlatform, '/sdp/<sdp_id>'
  
#### IaaS FVE Docker (_fnode_fve_docker.py_)

  Test, '/test'
  
  FogNodeInfo, "/info"
  
  FogVirtEngine, '/fve/<fve_id>'
