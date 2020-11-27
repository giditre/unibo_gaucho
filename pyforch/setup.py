from setuptools import setup, find_packages

setup(name= "forch",
  version= "2.01",
  author= "gaucho",
  description= "Fog Service Orchestration",
  packages= ["forch"],
  package_dir = {"forch": "src/forch"},
  package_data= {"forch": ["*.conf"]}
)