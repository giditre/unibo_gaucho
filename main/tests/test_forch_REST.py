import flask
import flask_restful

from pathlib import Path

import forch

from src.main.forch_main import FOM, FogServices

def test_services_get_200():
  app = flask.Flask(__name__)
  app.testing = True
  api = flask_restful.Api(app)
  api.add_resource(FogServices, '/services', '/services/<s_id>')
  with app.test_client() as tc:
    response = tc.get("/services")
    resp_json = response.get_json(force=True)
    assert isinstance(resp_json, dict), f"Response: {resp_json}"
    code = response.status_code
    assert code == 200, f"Response code: {code}"

def test_services_get_single_200():
  app = flask.Flask(__name__)
  app.testing = True
  api = flask_restful.Api(app)
  api.add_resource(FogServices, '/services', '/services/<s_id>')
  with app.test_client() as tc:
    response = tc.get("/services/APP001")
    resp_json = response.get_json(force=True)
    assert isinstance(resp_json, dict), f"Response: {resp_json}"
    code = response.status_code
    assert code == 200, f"Response code: {code} - is SLP running?"

def test_services_get_404():
  app = flask.Flask(__name__)
  app.testing = True
  api = flask_restful.Api(app)
  api.add_resource(FogServices, '/services', '/services/<s_id>')
  with app.test_client() as tc:
    response = tc.get("/services/asdasd")
    resp_json = response.get_json(force=True)
    assert isinstance(resp_json, dict), f"Response: {resp_json}"
    code = response.status_code
    assert code == 404, f"Response code: {code}"

def test_services_post_200():
  app = flask.Flask(__name__)
  app.testing = True
  api = flask_restful.Api(app)
  api.add_resource(FogServices, '/services', '/services/<s_id>')
  with app.test_client() as tc:
    response = tc.post("/services/APP001")
    resp_json = response.get_json(force=True)
    assert isinstance(resp_json, dict), f"Response: {resp_json}"
    code = response.status_code
    assert code == 200, f"Response code: {code} - is SLP running?"

def test_services_post_404():
  app = flask.Flask(__name__)
  app.testing = True
  api = flask_restful.Api(app)
  api.add_resource(FogServices, '/services', '/services/<s_id>')
  with app.test_client() as tc:
    response = tc.post("/services/asdasd")
    resp_json = response.get_json(force=True)
    assert isinstance(resp_json, dict), f"Response: {resp_json}"
    code = response.status_code
    assert code == 404, f"Response code: {code}"

def test_services_post_201():
  FOM.get_instance().set_project_list([forch.Project("default")])
  FOM.get_instance().load_source_list_from_json(str(Path(__file__).parent.joinpath("sources_catalog.json").absolute()))
  app = flask.Flask(__name__)
  app.testing = True
  api = flask_restful.Api(app)
  api.add_resource(FogServices, '/services', '/services/<s_id>')
  with app.test_client() as tc:
    response = tc.post("/services/APP001", json={"project":"default"})
    resp_json = response.get_json(force=True)
    assert isinstance(resp_json, dict), f"Response: {resp_json}"
    code = response.status_code
    assert code == 200, f"Response code: {code} - is SLP running?"