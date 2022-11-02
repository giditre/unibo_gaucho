class FogServices(Resource):
  # this GET replies with the active services, while available services (referred to as just "services") are discovered via SLP
  def get(self, s_id=""):
    as_list = [ {
      "service_id": s.get_service_id(),
      "base_service_id": s.get_base_service_id(),
      "node_id": s.get_node_id(),
      "instance_name": s.get_instance_name(),
      "instance_ip": s.get_instance_ip()
    } for s in FNVI.get_instance().get_active_service_list() ]
    return {
      "message": f"Found {len(as_list)} active service(s)",
      # "type": "FN_LS",
      "services": as_list
      }, 200

  def put(self, s_id):
    """Allocate service."""
    # TODO improve!!
    # request_json = flask.request.get_json(force=True)
    port = 0
    s_list = FNVI.get_instance().get_service_list()
    for s in s_list:
      if s.get_id() == s_id:
        port = s.get_node_list()[0].get_port() 
        active_s = forch.ActiveService(service_id=s_id)
        active_s.add_node(ipv4=FNVI.get_instance().get_ipv4(), port=port)
        FNVI.get_instance().update_active_service_list(active_s)
        break
    return {
      "message": f"Allocated service {s_id}",
      "port": port
      # "type": "FN_ALLC_OK",
      # "name": container_name,
      # "ip": container_ip, # TODO change in IP visible from outside
      # "port_mappings": port_mappings
      }, 200

  def post(self, s_id:str):
    """Deploy service."""

    request_json = flask.request.get_json(force=True)

    assert forch.InstanceConfiguration.BASE.value in request_json, f"Must specify a base service"
    assert forch.ServiceCategory.IAAS.value in request_json[forch.InstanceConfiguration.BASE.value], f"Must specify valid base service ({forch.ServiceCategory.IAAS.value}xxx)"
    base_id = request_json[forch.InstanceConfiguration.BASE.value]

    if base_id == forch.FogServiceID.DOCKER.value:
      assert forch.InstanceConfiguration.IMAGE.value in request_json, f"Must specify image in {request_json}"
      image_name = request_json[forch.InstanceConfiguration.IMAGE.value]

      if "instance_conf" in request_json:
        instance_conf_dict = request_json["instance_conf"]

        # preliminary configuration
        # if a network configuration is requested, check that the network exists
        if forch.DockerContainerConfiguration[forch.InstanceConfiguration.ATTACH_TO_NETWORK.value].value in instance_conf_dict:
          network_name = instance_conf_dict[forch.DockerContainerConfiguration[forch.InstanceConfiguration.ATTACH_TO_NETWORK.value].value]
          if FNVI.get_instance().docker_network_exists(network_name) == False:
            logger.debug(f"Network {network_name} does not exist")
            # create it, based on network configuration info in the JSON
            # these configs are assumed to be compatible with the employed Docker method
            network_conf_dict = request_json["network_conf"] # TODO avoid hardcoding string
            FNVI.get_instance().docker_network_create_with_bridge(network_name, **network_conf_dict)
            
      else:
        instance_conf_dict = {
          forch.DockerContainerConfiguration[forch.InstanceConfiguration.DETACH.value].value: True,
          forch.DockerContainerConfiguration[forch.InstanceConfiguration.KEEP_STDIN_OPEN.value].value: True,
          forch.DockerContainerConfiguration[forch.InstanceConfiguration.ALLOCATE_TERMINAL.value].value: True,
          forch.DockerContainerConfiguration[forch.InstanceConfiguration.FORWARD_ALL_PORTS.value].value: True
        }

      container = FNVI.get_instance().deploy_container_docker(s_id, image_name, **instance_conf_dict)

      assert container is not None, f'Error deploying service {s_id}, check image name "{image_name}"'
      assert container != b'', f'Error deploying service {s_id}, check run parameters'

      # refresh attrs dictionary
      container.reload()
      container_name = container.name # equivalent to container.attrs["Name"].strip("/")
      container_ip = container.attrs["NetworkSettings"]["IPAddress"]
      if not container_ip:
        container_ip = container.attrs["NetworkSettings"]["Networks"][container.attrs["HostConfig"]["NetworkMode"]]["IPAddress"]
      
      
      # port_mappings = [ f'{host_port_dict["HostIp"]}:{host_port_dict["HostPort"]}->{container_port}'
      #   for host_port_dict in container.attrs["NetworkSettings"]["Ports"][container_port]
      #   for container_port in container.attrs["NetworkSettings"]["Ports"]
      #   ]
      # equivalent to
      port_mappings = {}
      ports_dict = container.attrs["NetworkSettings"]["Ports"]
      for container_port in ports_dict:
        for host_port_dict in ports_dict[container_port]:
          # port_map = f'{host_port_dict["HostIp"]}:{host_port_dict["HostPort"]}->{container_port}'
          # port_mappings[host_port_dict["HostPort"]] = container_port
          port_mappings[container_port] = host_port_dict["HostPort"]
          # logger.debug(port_map)
      
      logger.debug(f"Deployed service {s_id} using image {image_name} on container {container_name} with address {container_ip} and ports {port_mappings}")
      
      if s_id.startswith('LAF'):

        entry = {  
          "IAAS": {
            "{id}".format(id=s_id): {
              "thumbnail": "",
              "protocol": "http",
              "path": "",
              "port": "{0}".format(port_mappings['80/tcp']),
              "name": "docker",
              "descr": "Docker",
              "lifetime": 65535
            }
          }
        }

        with open("/home/gaucho/unibo_gaucho/main/src/main/fnode_services.json", "r") as f:
          data = json.load(f)

        data.append(entry)

        with open("/home/gaucho/unibo_gaucho/main/src/main/fnode_services.json", "w") as f:
          json.dump(data, f)

        FNVI.get_instance().load_service_list_from_json(str(Path(__file__).parent.joinpath(local_config["services_json"]).absolute()))
        FNVI.get_instance().register_service_list()

      return {
        "message": f"Deployed service {s_id} on {base_id} with image {image_name}",
        # "type": "FN_DEPL_OK",
        "name": container_name,
        "ip": container_ip,
        "port_mappings": port_mappings
        }, 201

    elif base_id == "FVExxx":
      # to be implemented if node supports different FVE other than Docker
      pass
    else:
      return {
        "message": f"Unknown base service {base_id}",
        # "type": "FN_DEPL_OK",
        # "name": container_name,
        # "ip": container_ip, # TODO change in IP visible from outside
        # "port_mappings": port_mappings
        }, 404

  def delete(self, s_id=""):
    if s_id:
      FNVI.get_instance().destroy_service(s_id)
      return {
        "message": f"Deleted services matching {s_id}",
        # "type": "FN_DEL_OK",
        }, 200
    else:
      FNVI.get_instance().destroy_all_services()
      return {
        "message": f"Deleted all services",
        # "type": "FN_DEL_OK",
        }, 200