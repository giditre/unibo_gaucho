fnode_app_stress.py
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(FogApplication, '/app/<app_id>')

fnode_fve_docker.py
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, "/info")
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

fnode_iaas.py
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, "/info")
  api.add_resource(FogApplicationList, '/apps')
  api.add_resource(FogApplication, '/app/<app_id>')
  api.add_resource(SoftDevPlatformList, '/sdps')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')
  api.add_resource(FogVirtEngineList, '/fves')
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

fnode_paas.py
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(SoftDevPlatformList, '/sdps')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')

fnode_saas.py
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(FogApplicationList, '/apps')
  api.add_resource(FogApplication, '/app/<app_id>')

fnode_sdp_python.py
  api.add_resource(Test, '/test')
  api.add_resource(FogNodeInfo, '/info')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')

forch_broker.py
  api.add_resource(Test, '/test')
  api.add_resource(FogApplication, '/app/<app_id>')
  api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')
  api.add_resource(FogVirtEngine, '/fve/<fve_id>')

forch_iaas_mgmt.py
  api.add_resource(Test, "/test")
  api.add_resource(ImageList, "/images")
  api.add_resource(FogApplication, "/app/<app_id>")
  api.add_resource(SoftDevPlatform, "/sdp/<sdp_id>")
  #api.add_resource(FogVirtEngine, "/fve/<fve_id>")

forch_rsdb.py
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

forch_user_api.py
api.add_resource(Test, '/test')
api.add_resource(FogApplicationList, '/apps')
api.add_resource(FogApplication, '/app/<app_id>')
api.add_resource(SoftDevPlatformList, '/sdps')
api.add_resource(SoftDevPlatform, '/sdp/<sdp_id>')
api.add_resource(FogVirtEngineList, '/fves')
api.add_resource(FogVirtEngine, '/fve/<fve_id>')
api.add_resource(FogGateway, '/fgw/<node_id>/<node_port>', '/fgw/<node_id>/<node_port>/<path>')

