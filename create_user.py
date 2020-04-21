import sys
import json
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import argparse

parser = argparse.ArgumentParser()
  
#parser.add_argument("mand-arg", help="Mandatory positional argument.")
parser.add_argument("--user", help="Username", required=True)
parser.add_argument("--pwd", help="Password", required=True)
parser.add_argument("--db", help="User database", required=True)
parser.add_argument("--admin", help="Flag this user as administrator, default: False", action="store_true", default=False)

args = parser.parse_args()

print("CLI args: {}".format(vars(args)))

user_name = args.user
user_pwd = args.pwd
db_fname = args.db
is_admin = args.admin

# open db file
try:
  with open(db_fname) as f:
    user_db = json.load(f)
except FileNotFoundError as e:
  r = input("File {} not found. Create it? [y/n] ".format(db_fname))
  if r == "y":
    user_db = {}
    with open(db_fname, "w") as f:
      json.dump(user_db, f)
  else:
    sys.exit("Aborted.")
except json.JSONDecodeError as e:
  r = input("File {} is not formatted as a valid JSON. Overwrite it? [y/n] ".format(db_fname))
  if r == "y":
    user_db = {}
    with open(db_fname, "w") as f:
      json.dump(user_db, f)
  else:
    sys.exit("Aborted.")
 
# check if user already exists
if user_name in [ user_db[uid]["name"] for uid in user_db ]:
  r = input("User named {} already exists in db. Overwrite it? [y/n] ".format(user_name))
  if r != "y":
    sys.exit("Aborted.")

# generate random id for user making sure there are no collisions
user_id = str(uuid.uuid4())
while user_id in user_db:
  user_id = str(uuid.uuid4())

# generate hash for user password
user_pwd_hash = generate_password_hash(user_pwd, method='sha256')

user = {
  "id": user_id,
  "name": user_name,
  "password": user_pwd_hash,
  "is_admin": is_admin
}

print("Genrated user entry: {}".format(user))

user_db[user_id] = user

with open(db_fname, "w") as f:
  json.dump(user_db, f)

