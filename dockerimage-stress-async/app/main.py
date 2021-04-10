from multiprocessing import Process, cpu_count
import time
import json

from fastapi import FastAPI, Response, status
from pydantic import BaseModel
from typing import Optional, List, Dict

### logging configuration

# import logging
# from fastapi.logger import logger as fastapi_logger

# gunicorn_error_logger = logging.getLogger("gunicorn.error")
# gunicorn_logger = logging.getLogger("gunicorn")
# uvicorn_access_logger = logging.getLogger("uvicorn.access") # this is the loger to use for user messages
# uvicorn_access_logger.handlers = gunicorn_error_logger.handlers

# fastapi_logger.handlers = gunicorn_error_logger.handlers

# if __name__ == "__main__":
#   fastapi_logger.setLevel(logging.DEBUG)
# else:
#   fastapi_logger.setLevel(gunicorn_logger.level)

### stress handler

class StressHandler():
  def __init__(self) -> None:
    self.stress_process_list : List[Process] = []

  def get_stress(self) -> Dict:
    with open("/app/stress.json") as f:
      stress_json = json.load(f)
    return stress_json

  def create_stress(self, load: int, timeout: int) -> int:
    # TODO: improve
    if load < 0:
      n_cpu = min(abs(load), cpu_count())
    else:
      n_cpu = int( cpu_count() * load/100 )
    end_t = int(time.time()) + timeout

    if n_cpu > 0:

      # TODO: IMPROVE
      with open("/app/stress.json") as f:
        stress_json = json.load(f)
      n_cpu = n_cpu + int(stress_json["args"]["cpu"])

      print(f"Stressing {n_cpu} CPUs for {timeout} seconds...")
      stress_json = {
          "args": {
            "cpu": n_cpu
          },
          "end_t": end_t
        }

      # try:
      #   with open("/app/stress.json") as f:
      #     stress_json = json.load(f)
      # except:
      #   pass
      
      with open("/app/stress.json", "w") as f:
        json.dump(stress_json, f)

    return n_cpu

  def remove_stress(self) -> None:
    stress_json = {
          "args": {},
          "end_t": 0
        }
    with open("/app/stress.json", "w") as f:
      json.dump(stress_json, f)

stress_handler = StressHandler()

### API

app = FastAPI()

@app.get("/info", status_code=status.HTTP_200_OK)
def info():
  return {
      "message": "I'm alive!",
      "time": f"{int(time.time())}"
    }

@app.get("/stress", status_code=status.HTTP_200_OK)
def stress_info() -> Dict:
  stress_dict = stress_handler.get_stress()
  # return {
  #   "message": f"Got stress configuration.",
  #   "data": stress_dict
  # }
  return stress_dict

class StressConf(BaseModel):
  load: int
  timeout: Optional[int] = 10

@app.post("/stress", status_code=status.HTTP_202_ACCEPTED)
def stress_action(response: Response, stress_conf: StressConf) -> int:
  print(f"stress_conf: {vars(stress_conf)}")

  load = stress_conf.load
  timeout = stress_conf.timeout

  # launch stress handler, which returns asyncronously the number of CPUs stressed based on requested load
  n_cpu = stress_handler.create_stress(load, timeout)

  if n_cpu == 0:
    response.status_code = status.HTTP_400_BAD_REQUEST
    return {
      "message": f"Set load >= {int(100/cpu_count())} or no CPU will be stressed.",
      "n_cpu": n_cpu
    }
  
  return {
    "message": f"Stressing {n_cpu} CPUs for {timeout} seconds...",
    "n_cpu": n_cpu
  }

@app.delete("/stress", status_code=status.HTTP_200_OK)
def stress_remove() -> None:
  stress_handler.remove_stress()
  return {
    "message": f"Stopped stressing."
  }