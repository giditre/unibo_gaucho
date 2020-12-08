<img src="/FORCH_logo.png" width="150" align="right">

# UniBo GAUChO: FORCH

Introducing FORCH, a modular system for Fog Orchestrations container-based resorce allocation, developed in the context of project GAUChO by the team of the University of Bologna.

FORCH is designed for managing allocation of services in a Fog infrastructure, where efficiency, flexibility and dinamicity are key aspects. FORCH is composed of a set of components, each with its own role, communicating with the other components through their REST API. FORCH also relies on an "agent" module running in each Fog node, offering a REST API as well, employed to manage resources on the specifc node.

This PoC implementation is written in Python3. Its REST API is built using Flask RESTful, and its intended use is research and development purposes only - it is not suitable for production enviroments (yet), due to limited use of security mechanisms.

## Setting up the environment

FORCH modules (including orchestrator and agent modules) require the machines running them to offer some functionalities for monitoring and container management. Therefore, Zabbix (the employed monitoring system) and Docker (the virtualization engine of choice for this PoC implementation) must be installed and configured on the relevant nodes before running FORCH and its agent modules.

The general idea is to run FORCH on a machine and Fog nodes separate machines. It is important that these machienes can reach one another through the network.

### Install Zabbix

The following instructions cover the installation of the Zabbix monitoring system.

**NOTE:** Zabbix Server must be installed on the machine running the *forch* component of FORCH, while Zabbix Agent must be installed on each Fog node.

#### Zabbix Server

The following set of operation is the one followed to reach correct functioning of the Zabbix moniroting system on our development environment. Our set refers to **Zabbix version 4.4**. It is slightly different than the [installation instructions](https://www.zabbix.com/documentation/4.4/manual/installation/getting_zabbix) provided in the official Zabbix documentation, as some steps did not appear to work as they were described there. Plus, this is mostly specific to **Ubuntu 18.04**.

First, install required web and database packages (loosely based on [these instructions](https://www.digitalocean.com/community/tutorials/how-to-install-linux-apache-mysql-php-lamp-stack-ubuntu-18-04)):
```bash
sudo apt install -y apache2 mysql-server
```
Run the configuration tool of mySQL:
```bash
sudo mysql_secure_installation
```
Choose a password (e.g., _mypassword123_), and confirm all the rest with _y_.

Set the system firewall to allow web traffic:
```bash
sudo ufw app list
sudo ufw app info "Apache Full"
sudo ufw allow in "Apache Full"
```
Install php libraries
```bash
sudo apt install php libapache2-mod-php php-mysql
```
Restart the apacher web server:
```bash
sudo systemctl restart apache2
```
Install the [PHP FastCGI Process Manager](https://www.php.net/manual/en/install.fpm.php) module:
```bash
sudo apt install php-fpm
```
Add Zabbix repo to the machine's known repositories:
```bash
wget https://repo.zabbix.com/zabbix/4.4/ubuntu/pool/main/z/zabbix-release/zabbix-release_4.4-1+bionic_all.deb
sudo dpkg -i zabbix-release_4.4-1+bionic_all.deb
```
Install Zabbix server components:
```bash
sudo apt update && sudo apt install -y zabbix-server-mysql zabbix-frontend-php zabbix-apache-conf
```
Authenticate as the user root to mySQL by the previously configured password (e.g., _mypassword123_) when requested:
```bash
sudo mysql -uroot -p
```
Inside the mySQL CLI, configure access as the _zabbix_ user:
```
create database zabbix character set utf8 collate utf8_bin;
grant all privileges on zabbix.* to zabbix@localhost identified by 'zabbix';
flush privileges;
quit;
```
Initialize the database using password _zabbix_ (this step might take a while to complete, do not interrupt it even if it does not print any output):
```bash
zcat /usr/share/doc/zabbix-server-mysql/create.sql.gz | mysql -uzabbix -p zabbix
```
Configure access to the Zabbix Server by editing the configuration file
```bash
sudo vim /etc/zabbix/zabbix_server.conf
```
and setting a password in the variable 'DBPassword' (e.g., _zabbix_).

Set the correct local timezone by editing the configuration file
```bash
sudo vim /etc/zabbix/apache.conf
```
and setting `php_value date.timezone Europe/Rome` (or any other local timezone).

Restart the web server and check its status:
```bash
sudo systemctl restart apache2
sudo systemctl status apache2
```
Restart the Zabbix server and enable it for automatic start at system boot:
```bash
sudo systemctl restart zabbix-server
sudo systemctl enable zabbix-server
```
Check the correct installation by navigating from a browser to the `http://myzabbixserver/zabbix/` where _myzabbixserveraddress_ is the IP address or hostname of the machine where the server is installed and running. If everything went well, you should find a Welcome page. Click "Next" for every step, and at the end you should see a message saying "_Congratulations! You have successfully installed Zabbix frontend. Configuration file "/usr/share/zabbix/conf/zabbix.conf.php" created._"

#### Zabbix Agent

The installation of the Zabbix agent module only is much lighter than the installation of the Zabbix server.

Add Zabbix repo to the machine's known repositories:
```bash
wget https://repo.zabbix.com/zabbix/4.4/debian/pool/main/z/zabbix-release/zabbix-release_4.4-1+buster_all.deb
sudo dpkg -i zabbix-release_4.4-1+buster_all.deb
```
Install Zabbix agent components:
```bash
sudo apt update && sudo apt install -y zabbix-agent
```
Generate a PSK key specific to this agent, and save it to a file:
```bash
sudo sh -c "openssl rand -hex 32 > /etc/zabbix/zabbix_agentd.psk"
cat /etc/zabbix/zabbix_agentd.psk
```
The PSK key will be also used later on for the GUI configuration of each agent. You can always retrieve it with:
```bash
cat /etc/zabbix/zabbix_agentd.psk
```
Configure the communication of this agent with the Zabbix server by editing the configuration file:
```bash
sudo vim /etc/zabbix/zabbix_agentd.conf
```
and filling in the required details:
```
Server=_myzabbixserveraddress_
TLSConnect=psk
TLSAccept=psk
TLSPSKIdentity=PSK 001
TLSPSKFile=/etc/zabbix/zabbix_agentd.psk
```
where _myzabbixserveraddress_ is the IP address or hostname of the machine where the server is installed and running.

Restart the Zabbix agent, check its status, and enable it for automatic start at system boot:
```bash
sudo systemctl restart zabbix-agent
sudo systemctl status zabbix-agent
sudo systemctl enable zabbix-agent
```
Set the firewall to allow the communication between the Zabbix agent and the Zabbix server (in this case allowing the default port, which however can be changed):
```bash
sudo ufw allow 10050/tcp
```

#### Register Agents in the Server

Every node hosting an agent (i.e., a _host_) must be registered to the Zabbix Server. We can do it manually via the server's Web GUI, or configure host discovery and have hosts to register automatically.

#### ...manually

Browse to `http://myzabbixserver/zabbix/` and [log in](https://www.zabbix.com/documentation/4.4/manual/quickstart/login) as administrator with username *Admin* and password *zabbix*.

Under tab *Configuration > Hosts*, in the top right corner click on *Create host*, and insert the details of the fog node you want to register, specifying a host name, a template (e.g., *Template OS Linux by Zabbix agent*) and the node's IP address (which must be reachable from the Zabbix server), leaving the port to 10050 if you have not changed it in the server's configuration. In sub-tab *Encryption* set *Connections ot Host* to *PSK*, and set *Connections from host* to *PSK* only (uncheck the other checkboxes). Fill in the field *PSK* identity with the *TLSPSKIdentity* set at key creation, and fill in the field *PSK* with the PSK itself generated previously. Confirm with *Add* and go back to *Configuration > Hosts*, where you should see the new host connected to the server and reporting data (if you don't, wait a couple minutes and refresh the page).

#### ...setting up host discovery

Browse to `http://myzabbixserver/zabbix/` and [log in](https://www.zabbix.com/documentation/4.4/manual/quickstart/login) as administrator with username *Admin* and password *zabbix*.

Warning: for the moment, this configuration does not cover setting up PSK encryption on discovered nodes.

First, we are going to specify what to do ("actions") with the discovered nodes, then we are going to configure the node discovery.

Under tab *Configuration > Actions*, in the top right corner select *Event source: Discovery* then *Create action*. Set an arbitrary *Name*, and the required conditions, e.g., *Discovery check equals Local network: Zabbix agent "system.hostname"*, *Discovery status equals Up*, and *Service type equals Zabbix agent*. Enable this set of actions. Then move to *Operations* section, and specify what to do with nodes matching the preconfigured actions, e.g., *Add to host groups: Linux servers* and *Link to templates: Template OS Linux by Zabbix agent*. Confirm the creation of the action-opration rule.

Move to tab *Configuration > Discovery*, in the top right corner click on *Create discovery rule*, or edit the defalt one that is already there. Give it an arbitrary *Name*. Use *No proxy*. Insert a proper *IP range*, e.g., *10.15.5.1-254* (remark: use an IP range that is reachable from the Zabbix Server machine). Specify an *Update interval*, e.g., *30s* or *1h*. Specify any *Checks* that characterize a discovered node, e.g., *Zabbix agent "system.hostname"*. Select an *Uniqueness criteria*, select what to use as *Host name* and *Visible name*. Check *Enable* and confirm the creation of the discovery rule.

If everything went fine, after at least one *Update interval*, any configured Zabbix agent should appear under tab *Monitoring > Discovery*, and should be added to the monitored hosts, visible in *Configuration > Hosts*.

### Install Docker

Docker must be installed on machines acting as IaaS fog nodes. The installation instructions for Docker can be found [here](https://docs.docker.com/engine/install/). The following set of operation is the one followed to reach correct functioning of Docker Engine on the development system.

#### ...on Ubuntu

The following instructions for the installation of Docker on Ubuntu are taken from [here](https://docs.docker.com/engine/install/ubuntu/).

Make sure no Docker component is installed in the system:
```
sudo apt-get remove docker docker-engine docker.io containerd runc
```
Install authentication-related packages and add the Docker repository:
```
sudo apt-get update && sudo apt-get -y install apt-transport-https ca-certificates curl gnupg-agent software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-key fingerprint 0EBFCD88
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
```
Install Docker packets:
```
sudo apt-get update && sudo apt-get -y install docker-ce docker-ce-cli containerd.io
```
Remove the need for `sudo` with:
```
sudo groupadd docker
sudo gpasswd -a $USER docker
newgrp docker
```
Test the correct installation of docker with:
```
docker run hello-world
```

#### ...on Raspberry Pi

```
sudo apt-get remove docker docker-engine docker.io containerd runc
sudo apt-get update && sudo apt-get install apt-transport-https ca-certificates software-properties-common -y
curl -fsSL get.docker.com -o get-docker.sh && sh get-docker.sh
sudo usermod -aG docker $USER
sudo curl https://download.docker.com/linux/raspbian/gpg | sudo apt-key add -
```
Add the Raspbian Docker repo by editing
```
sudo vim /etc/apt/sources.list
```
and adding the line:
```
deb https://download.docker.com/linux/raspbian/ stretch stable
```
Upgrade the installation and make Docker active on boot:
```
sudo apt-get update && sudo apt-get -y upgrade
sudo systemctl enable docker.service
sudo systemctl restart docker.service
sudo systemctl status docker.service
```
Check the correct installation
```
docker info
docker run hello-world
```

# WORK IN PROGRESS

### Install Python modules

The following instructions apply for the machine(s) hosting the FORCH components, as well as for those acting as fog nodes.

It is suggested (but not strictly required) to operate inside of a [venv](https://docs.python.org/3.6/library/venv.html).

Make sure the following Python3 modules are installed on every machine:
```bash
flask_restful
requests
docker
pyzabbix
```
This can also be achieved by cloning the repo, then moving into the directory, and let pip3 do the work:
```bash
git clone giditre/unibo_gaucho
cd unibo_gaucho/
pip3 install -r requirements.txt
```

#### Installation of the slp module

In addition to the previously mentioned module, the module *slp* is required too. However, to the date of writing, this module is not available on the Python package repos, therefore it must be installed from source. The procedure makes use of some development packages, that **on Ubuntu 18.04** can be installed with:
```bash
sudo apt -y install pkg-config bison automake flex libtool
```
Then clone the repo of *libslp* and install its content with:
```bash
git clone https://github.com/openslp-org/openslp.git
cd openslp/openslp/
./autogen.sh
sudo ./configure --prefix /usr
sudo make
sudo make install
ls -l slpd/slpd libslp/.libs/libslp.so
```
Move back to the home directory and clone the repo of the Python module *slp* with:
```bash
cd
git clone https://github.com/tsmetana/python-libslp.git
```
In the cloned repo directory
```bash
cd python-libslp/
```
edit file *configure.ac* modifying the line of *PKG_CHECK_MODULES* to:
```bash
PKG_CHECK_MODULES(Python, python3 >= 3.0,,)
```
Then proceed with the installation:
```bash
autoreconf -fvi
autoconf
sudo ./configure
sudo make
sudo make install
```
In the *src* directory (where a file called *slp.so* should be)
```bash
cd src/
```
create file *setup.py* and add the following content to it:
```python
from distutils.core import setup
setup (name = 'slp',
       version = '0.1',
       author = "tsmetana",
       description = """SLP Library""",
       py_modules = ["slp"],
       packages=[''],
       package_data={'': ['slp.so']},
       )
```
Then finally install the module (from within the *src* directory) with:
```bash
pip3 install . --user
```

Test the correct installation of the module by opening a python3 terminal and importing the slp module with:
```python
import slp
```

## Running the FORCH ecosystem

FORCH consists of multiple independent components, which may be run on the same machine or on separate machines, as the communication between them happens via REST calls. However, in the development phase, for security purposes it is suggested to run all of the FORCH components on a single machine and make all of them listen only on the loopback interface (127.0.0.1), except for the User Access component (*forch_user_access.py*) which is the only one using HTTPS (as opposed to the others using unencrypted HTTP).

### Recommended: launching components simultaneously

This is the easiest approach, which launches all FORCH components on a single machine, monitoring their output on a single terminal. From the machine you want to run FORCH, inside of the *unibo_gaucho* folder, launch:
```bash
./run_forch.sh
```
Then, on every machine acting as fog node, clone the repo, then inside of the *unibo_gaucho* folder launch the relevant *fnode* component with:
```bash
./run_fnode_iaas.sh < -i | -p | -s >
```
Where the option "i" or "p" or "s" will make the node act as IaaS, PaaS os SaaS respectively. Only one possible mode at a time. If you specify multiple option, only the last one will count.

### Alternative: launching components separately

This is the advanced and more customizable From inside of the repo directory, run each of the components with
```bash
python3 <component_file_name> <IP_address> <TCP_port>
```
for example:
```bash
python3 forch_user_access.py 0.0.0.0 5001
```
or
```bash
python3 forch_broker.py 127.0.0.1 5002
```

The address 0.0.0.0 makes the components listen on all of the machine's interfaces, while 127.0.0.1 makes it listen only on the loopback interface.

The choice of the TCP port is arbitrary. However, by default the ports are mapped this way:
Component | Port
----------|-----
forch_user_access.py | 5001
forch_broker.py | 5002
forch_rsdb.py | 5003
forch_iaas_mgmt.py | 5004
fnode_saas.py / fnode_paas.py / fnode_iaas.py | 5005

Running a component with a customized port required the other components to be instructed on the choice. This can be achieved by specifying comman line arguments for every component detailing the choice of IP addresses and ports. For the list of available CLI arguments for every component and for their usage, refer to the inline help of each component, by running:
```bash
python3 <component_file_name> --help
```

In any case, it is necessary that every component is within reach (network-wise) of all the other ones. This also includes _fnode_ components.

The monitoring system [Zabbix](www.zabbix.com) must be configured on the node running _forch_rsdb.py_ (which accesses Zabbix through the Python module _pyzabbix_)

## Using FORCH

### FORCH REST API

#### User Access (_forch_user_access.py_)

  * ##### Test

    * `GET /test`

      **Response code:** 200

      **Sample response content:**
      ```json
      {
        "message": "This endpoint is up!"
      }
      ```

  * ##### APPs

    * `GET /apps`
    
      **Response code:** 200

      **Sample response content:**
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
    
      **Sample request URL:** `/app/APP002`

      Possible responses:

      **Response code:** 200

      **Sample response content:**
      ```json
      {
        "message": "APP APP002 available",
        "type": "OBR_APP_AVLB_S",
        "node_class": "S",
        "node_id": "10317",
        "service_port": 38538
      }
      ```
      
      or
      
      **Response code:** 201

      **Sample response content:**
      ```json
      {
        "message": "APP APP003 allocated",
        "type": "OBR_APP_ALLC_I",
        "node_class": "I",
        "node_id": "10313",
        "service_port": 32784
      }
      ```

      or

      **Response code:** 503

      **Sample response content:**
      ```json
      {
        "message": "APP APP001 not deployed and no available IaaS node",
        "type": "OBR_APP_NAVL_I"
      }
      ```
      ---
      **Sample request URL:** `/app/APP007`

      **Response code:** 404
      
      **Sample response content:**
      ```json
      {
        "message": "APP APP007 not defined",
        "type": "OBR_APP_NDEF"
      }
      ```

  * ##### SDPs

    * `GET /sdps`
    
      **Response code:** 200

      **Sample response content:** 
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
    
      **Sample request URL:** `/sdp/SDP001`

      Possible responses:

      **Response code:** 200

      **Sample response content:** 
      ```json
      {
        "message": "SDP SDP001 available",
        "type": "OBR_SDP_AVLB_P",
        "node_class": "P",
        "node_id": "10315",
        "service_port": 30674
      }
      ```

      or

      **Response code:** 201

      **Sample response content:**
      ```json
      {
        "message": "SDP SDP001 allocated",
        "type": "OBR_SDP_ALLC_I",
        "node_class": "I",
        "node_id": "10313",
        "service_port": 32785
      }
      ```

      or

      **Response code:** 503

      **Sample response content:**
      ```json
      {
        "message": "SDP SDP001 not deployed and no available IaaS node",
        "type": "OBR_SDP_NAVL_I"
      }
      ```
      ---
      **Sample request URL:** `/sdp/SDP007`

      **Response code:** 404

      **Sample response content:**
      ```json
      {
        "message": "SDP SDP007 not defined",
        "type": "OBR_SDP_NDEF"
      }
      ```

  * ##### FVEs

    * `GET /fves`
    
      **Response code:** 200

      **Sample response content:** 
      ```json
      {
        "FVE001": {
          "name": "docker",
          "descr": "Docker engine"
        }
      }
      ```
    
    * `GET /fve/<fve_id>`
    
      **Sample request URL:** `/fve/FVE001`

      Possible responses:

      **Response code:** 200

      **Sample response content:** 
      ```json
      {
        "message": "FVE FVE001 available",
        "type": "OBR_FVE_AVLB_I",
        "node_class": "I",
        "node_id": "10313",
        "service_port": 36683
      }
      ```
      
      or 

      **Response code:** 503

      **Sample response content:**
      ```json  
      {
        "message": "FVE FVE001 is deployed but no available IaaS node",
        "type": "OBR_FVE_NAVL_I"
      }
      ```
      ---
      **Sample request URL:** `/fve/FVE002`

      **Response code:** 503

      **Sample response content:**
      ```json
      {
        "message": "FVE FVE002 not deployed",
        "type": "OBR_FVE_NDEP"
      }
      ```
      ---
      **Sample request URL:** `/fve/FVE007`

      **Response code:** 404

      **Sample response content:**
      ```json  
      {
        "message": "FVE FVE007 not defined",
        "type": "OBR_FVE_NDEF"
      }
      ```

  * ##### Fog Gateway to allocated services

    * `GET /fgw/<node_id>/<node_port>`

      
    
    * `POST /fgw/<node_id>/<node_port>`
    
    * `GET /fgw/<node_id>/<node_port>/<path>`
    
    * `POST /fgw/<node_id>/<node_port>/<path>`

#### Broker (_forch_broker.py_)

  * ##### Test

    * GET `/test`
   
  * ##### FogApplication

    * GET `/app/<app_id>`
   
  * ##### SoftDevPlatform

    * GET `/sdp/<sdp_id>`
   
  * ##### FogVirtEngine

    * GET `/fve/<fve_id>`

#### Resource Datababe (_forch_rsdb.py_)

  * ##### Test

    * GET `/test`
  
  * ##### FogNodeList

    * GET `/nodes`
  
  * ##### FogNode

    * GET `/node/<node_id>`
  
  * ##### FogMeasurements

    * GET `/meas`
  
  * ##### FogApplicationCatalog

    * GET `/appcat`
  
  * ##### FogApplicationList

    * GET `/apps`
  
  * ##### FogApplication

    * GET `/app/<app_id>`
  
  * ##### SoftDevPlatformCatalog

    * GET `/sdpcat`
  
  * ##### SoftDevPlatformList

    * GET `/sdps`
  
  * ##### SoftDevPlatform

    * GET `/sdp/<sdp_id>`
  
  * ##### FogVirtEngineCatalog

    * GET `/fvecat`
  
  * ##### FogVirtEngineList

    * GET `/fves`
  
  * ##### FogVirtEngine

    * GET `/fve/<fve_id>`

#### IaaS node management (_forch_iaas_mgmt.py_)

  * ##### Test

    * GET `/test`
  
  * ##### ImageList

    * GET `/images`
  
  * ##### FogApplication

    * GET `/app/<app_id>`
  
  * ##### SoftDevPlatform

    * GET `/sdp/<sdp_id>`
  
  * ##### FogVirtEngine

    * GET `/fve/<fve_id>`


### Fog Node management API

#### SaaS node management agent (_fnode_saas.py_)

  * ##### Test

    * GET `/test`
  
  * ##### FogNodeInfo

    * GET `/info`
  
  * ##### FogApplicationList

    * GET `/apps`
  
  * ##### FogApplication

    * GET `/app/<app_id>`
  
#### PaaS node management agent (_fnode_paas.py_)

  * ##### Test

    * GET `/test`
  
  * ##### FogNodeInfo

    * GET `/info`
  
  * ##### SoftDevPlatformList

    * GET `/sdps`
  
  * ##### SoftDevPlatform

    * GET `/sdp/<sdp_id>`

#### IaaS node management agent (_fnode_iaas.py_)

  * ##### Test

    * GET `/test`
  
  * ##### FogNodeInfo

    * GET `/info`
  
  * ##### FogApplicationList

    * GET `/apps`
  
  * ##### FogApplication

    * GET `/app/<app_id>`
  
  * ##### SoftDevPlatformList

    * GET `/sdps`
  
  * ##### SoftDevPlatform

    * GET `/sdp/<sdp_id>`
  
  * ##### FogVirtEngineList

    * GET `/fves`
  
  * ##### FogVirtEngine

    * GET `/fve/<fve_id>`

### Fog Node Service API

#### SaaS APP stress (_fnode_app_stress.py_)

  * ##### Test

    * GET `/test`
  
  * ##### FogNodeInfo

    * GET `/info`
  
  * #####  FogApplication

    * POST  `/app/<app_id>`

      **Sample request URL:** `/app/APP002`

      **Sample Request Data:**
      ```json
      {
          "cpu": 1,
          "timeout": 10
      }
      ```

#### PaaS SDP Python3 (_fnode_sdp_python.py_)

  * ##### Test

    * GET `/test`
  
  * ##### FogNodeInfo `/info`
    
  * ##### SoftDevPlatform

    * POST `/sdp/<sdp_id>`

      **Sample request URL:** `/sdp/SDP001`

      **Sample Request Data:**
      ```json
      {
        "code": "a=123456\nprint(str(a))",
        "return_output": true
      }
      ```

      **Response code:** 200

      **Sample response content:**
      ```json 
      {
        "message": "Finished running SDP SDP001",
        "type": "SDP_PYTH_EXEC",
        "params": {
          "code": "a=123456\nprint(str(a))",
          "return_output": true
        },
        "hostname": "gaucho-fnode-vm2",
        "output": "123456"
      }
      ```
  
#### IaaS FVE Docker (_fnode_fve_docker.py_)

  * ##### Test

    * GET `/test`
  
  * ##### FogNodeInfo

    * GET `/info`
  
  * ##### FogVirtEngine

    * GET `/fve/<fve_id>`
