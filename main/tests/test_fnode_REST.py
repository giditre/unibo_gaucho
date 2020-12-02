import forch

# from src.main.fnode_main import FogServices

# def test_services_get_200():
#   resource = FogServices()
#   assert isinstance(resource, FogServices), ""
#   response, code = resource.get()
#   assert isinstance(response, dict), f"Response: {response}"
#   assert isinstance(code, int), f"Response code: {code}"
#   assert code == 200, f"Response: {response}, response code: {code}"

# def test_services_get_single_200():
#   resource = FogServices()
#   assert isinstance(resource, FogServices), ""
#   response, code = resource.get("APP001")
#   assert isinstance(response, dict), f"Response: {response}"
#   assert isinstance(code, int), f"Response code: {code}"
#   assert code == 200, f"Response: {response}, response code: {code}"

# def test_services_get_404():
#   resource = FogServices()
#   assert isinstance(resource, FogServices), ""
#   response, code = resource.get("APP999")
#   assert isinstance(response, dict), f"Response: {response}"
#   assert isinstance(code, int), f"Response code: {code}"
#   assert code == 404, f"Response: {response}, response code: {code}"

# def test_services_post_200():
#   resource = FogServices()
#   assert isinstance(resource, FogServices), ""
#   response, code = resource.post("APP001")
#   assert isinstance(response, dict), f"Response: {response}"
#   assert isinstance(code, int), f"Response code: {code}"
#   assert code == 200, f"Response: {response}, response code: {code}"

# def test_services_post_404():
#   resource = FogServices()
#   assert isinstance(resource, FogServices), ""
#   response, code = resource.post("APP999")
#   assert isinstance(response, dict), f"Response: {response}"
#   assert isinstance(code, int), f"Response code: {code}"
#   assert code == 404, f"Response: {response}, response code: {code}"