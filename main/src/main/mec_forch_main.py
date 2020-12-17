import requests

response = requests.post("http://127.0.0.1:6001/services/APP004", json={"project":"mec-project"})

response_json = response.json()

print(f"{response_json}")

with open("/mnt/mqtt-mec/foghosts", "a") as f:
  f.write(f'{response_json["instance_ip"]} {response_json["instance_name"]}\n')

