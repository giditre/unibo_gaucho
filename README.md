<img src="/forch_logo.png" width="150" align="right">

# UniBo GAUChO: FORCH

Introducing FORCH, a modular system for Fog Orchestrations container-based resorce allocation, developed in the context of project GAUChO by the team of the University of Bologna.

This PoC implementation is written in Python3. Its REST API is built using Flask RESTful, and it is for research and development purposes only, as it is not safe for production enviroments.

### Installing

Make sure the following Python3 modules are installed via pip3:
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

### FORCH API

#### User Access (_forch_user_api.py_)

* Test

  > GET /test

    **Code:** 200 <br />
    **Sample content:** `{ "message" : "This endpoint is up!" }`

* APPs

  > GET /apps
  
  **Code:** 200 <br />
  **Sample Content:** `{"APP001": {"name": "httpd", "descr": "Apache web server"}, "APP002": {"name": "stress", "descr": "Stress host"}}`
  
  > GET /app/<app_id>
  
  **Code:** 200 <br />
  **Sample Content:** `{"message": "App APP001 allocated", "node_class": "I", "node_id": "10313", "service_port": "32772"}`
  
* SDPs

  > GET /sdps
  
  **Code:** 200 <br />
  **Sample Content:** `{"SDP001": {"name": "python", "descr": "Python3"}, "SDP002": {"name": "alpine", "descr": "Lightweight Ubuntu"}}`
  
  > GET /sdp/<sdp_id>
  
  **Code:** 200 <br />
  **Sample Content:** `{"message": "SDP SDP001 allocated", "node_class": "P", "node_id": "10315", "service_port": 35676}`
  
* FVEs

  > GET /fves
  
  **Code:** 200 <br />
  **Sample Content:** `{"FVE001": {"name": "docker", "descr": "Docker engine"}}`
  
  > GET /fve/<fve_id>
  
  **Code:** 200 <br />
  **Sample Content:** `{"message": "FVE FVE001 allocated", "node_class": "I", "node_id": "10313", "service_port": 37507}`
  
* Fog Gateway to allocated services

  > GET /fgw/<node_id>/<node_port>
  > POST /fgw/<node_id>/<node_port>
  > GET /fgw/<node_id>/<node_port>/<path>
  > POST /fgw/<node_id>/<node_port>/<path>

#### Broker (_forch_broker.py_)
  api.add_resource(Test, '/test')
  api.add_resource(FogApplication, '/app/<app_id>')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

#### Resource Datababe (_forch_rsdb.py_)
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeList, '/nodes')
  api.add_resource(FogNode, '/node/<node_id>')
  api.add_resource(FogMeasurements, '/meas')
  api.add_resource(FogApplicationCatalog, '/appcat')
  api.add_resource(FogApplicationList, '/apps')
  api.add_resource(FogApplication, '/app/<app_id>')
  api.add_resource(SoftDevPlatformCatalog, '/sdpcat')
  api.add_resource(SoftDevPlatformList, '/sdps')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')
  api.add_resource(FogVirtEngineCatalog, '/fvecat')
  api.add_resource(FogVirtEngineList, '/fves')
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

#### IaaS node management (_forch_iaas_mgmt.py_)
  api.add_resource(Test, "/test")
  api.add_resource(ImageList, "/images")
  api.add_resource(FogApplication, "/app/<app_id>")
  api.add_resource(SoftDevPlatform, "/sdp/<sdp_id>")
  #api.add_resource(FogVirtEngine, "/fve/<fve_id>")

### Fog Node management API

#### SaaS node management agent (_fnode_saas.py_)
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(FogApplicationList, '/apps')
  api.add_resource(FogApplication, '/app/<app_id>')
  
#### PaaS node management agent (_fnode_paas.py_)
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(SoftDevPlatformList, '/sdps')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')

#### IaaS node management agent (_fnode_iaas.py_)
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, "/info")
  api.add_resource(FogApplicationList, '/apps')
  api.add_resource(FogApplication, '/app/<app_id>')
  api.add_resource(SoftDevPlatformList, '/sdps')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')
  api.add_resource(FogVirtEngineList, '/fves')
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

### Fog Node Service API

#### SaaS APP stress (_fnode_app_stress.py_)
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(FogApplication, '/app/<app_id>')

#### PaaS SDP Python3 (_fnode_sdp_python.py_)
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')
  
#### IaaS FVE Docker (_fnode_fve_docker.py_)
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, "/info")
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')
