import flask
import flask_restful
import docker

import forch

from src.main.fnode_main import Test, FogServices

def test_test():
  app = flask.Flask(__name__)
  app.testing = True
  api = flask_restful.Api(app)
  api.add_resource(Test, '/test')
  with app.test_client() as test_client:
    response = test_client.get('/test')
    assert response.status_code == 200, ""
    resp_json = response.get_json(force=True)
    assert resp_json["type"] == "FN_TEST_OK", ""

def test_services_post_201():
  app = flask.Flask(__name__)
  app.testing = True
  api = flask_restful.Api(app)
  api.add_resource(FogServices, '/services', '/services/<s_id>')
  with app.test_client() as tc:
    response = tc.post('/services/APP001', json={"image_uri":"alpine"})
    assert response.status_code == 201, ""
    resp_json = response.get_json(force=True)
    assert resp_json["type"] == "FN_DEPL_OK", ""

def test_services_delete_200():
  app = flask.Flask(__name__)
  app.testing = True
  api = flask_restful.Api(app)
  api.add_resource(FogServices, '/services', '/services/<s_id>')
  with app.test_client() as tc:
    response = tc.delete('/services/APP001')
    assert response.status_code == 200, ""
    resp_json = response.get_json(force=True)
    assert resp_json["type"] == "FN_DEL_OK", ""