from setuptools import setup, find_packages

setup(name = "forch",
  version = "2.1",
  author = "gaucho",
  description = "Fog Service Orchestration",
  # packages = find_packages(where="forch"),
  packages = ["forch"],
  package_dir = {"forch": "src/forch"},
  package_data= {"forch": ["*.conf"]}
)