import time
duration = 60
n = 1 + int(time.time()) % 10
timeout = time.time() + float(duration) 
while time.time() < timeout:
  n*n
