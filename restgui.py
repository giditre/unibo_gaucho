from http.server import BaseHTTPRequestHandler, HTTPServer
from gpiozero.pins.mock import MockFactory
from gpiozero import Device, LED
from signal import pause
from socket import gethostname
from distutils.dir_util import copy_tree
import os
import shutil
from threading import Thread
import logging
import argparse
from time import sleep

### Logging setup

logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

### Command line argument parser

default_address = "0.0.0.0"
default_port = 6210

parser = argparse.ArgumentParser()
  
parser.add_argument("-a", "--address", help="IP address of this server. Default: {}".format(default_address), nargs="?", default=default_address)
parser.add_argument("-p", "--port", help="TCP port of this server. Default: {}".format(default_port), type=int, nargs="?", default=default_port)
parser.add_argument("-d", "--debug", help="Run in debug mode.", action="store_true", default=False)

args = parser.parse_args()

address = args.address
port = args.port
debug = args.debug

###

if debug:
  # Set the default pin factory to a mock factory
  Device.pin_factory = MockFactory()
  mounted_devices = set()

copy_thread = Thread()
move_thread = Thread()

###

gpio_dict = {}
gpio_dict["GPIO17"] = LED("GPIO17")

###

def shell_cmd(cmd): 
  logging.debug("shell command: {}".format(cmd))
  return os.system(cmd)

def is_mounted(device, debug=debug):
  if debug:
    global mounted_devices
    mounted = device in mounted_devices
  else:
    mounted = True if shell_cmd('grep -sq "{}" /proc/mounts'.format(device)) == 0 else False
  return mounted

def mount_all(debug=debug):
  if debug:
    global mounted_devices
    with open("/etc/fstab", "r") as f:
      #mounted_devices = [ line.split()[1].replace("/mnt/","") for line in f if "/mnt" in line ]
      for line in f:
        if "/mnt" in line:
          device = line.split()[1].replace("/mnt/","")
          mounted_devices.add(device)
    logger.debug("Debug mode - mounted devices: {}".format(mounted_devices))
    r = 0
  else:  
    r = shell_cmd("sudo mount -a")
  return r

def unmount(device, debug=debug):
  if debug:
    global mounted_devices
    mounted_devices.discard(device)
    r = 0
  else:
    r = shell_cmd("sudo umount -l /mnt/{}".format(device))
  return r

def clean_fname(fname, remove="", replace=" .-()[]", sep="_"):

  new_fname, ext = os.path.splitext(fname)

  for c in remove:
    new_fname = new_fname.replace(c, "")

  for c in replace:
    new_fname = new_fname.replace(c, sep)

  while "__" in new_fname:
    for i in range(len(new_fname)-1):
      if new_fname[i] == "_" and new_fname[i+1] == "_":
        new_fname = new_fname.replace("__", "_")
        break

  new_fname = new_fname.strip("_")

  return new_fname + ext
 
def clean_dirname(dirname, remove="", replace=" .-()[]", sep="_"):

  #new_fname, ext = os.path.splitext(fname)
  new_dirname = dirname

  for c in remove:
    new_dirname = new_dirname.replace(c, "")

  for c in replace:
    new_dirname = new_dirname.replace(c, sep)

  while "__" in new_dirname:
    for i in range(len(new_dirname)-1):
      if new_dirname[i] == "_" and new_dirname[i+1] == "_":
        new_dirname = new_dirname.replace("__", "_")
        break

  new_dirname = new_dirname.strip("_")

  #return new_fname + ext
  return new_dirname

def is_dir_empty(dir_path):
  return len(list(os.listdir(dir_path))) == 0

def copy_contents(src_dir_path, dst_dir_path, debug=debug):
  if debug:
    pass
  else:
    for curr_dir, subdirs, files in os.walk(src_dir_path, topdown=False):
      #logger.debug(print(curr_dir, subdirs, files))
      for fname in files:
        new_fname = clean_fname(fname)
        old_path = os.path.join(curr_dir, fname)
        new_path = os.path.join(curr_dir, new_fname)
        if new_path != old_path:
          logger.debug("RENAME", "{} -> {}".format(old_path, new_path))
          os.rename(old_path, new_path)

      for dirname in subdirs:
        new_dirname = clean_dirname(dirname)
        old_path = os.path.join(curr_dir, dirname)
        new_path = os.path.join(curr_dir, new_dirname)
        if new_path != old_path:
          logger.debug("RENAME", "{} -> {}".format(old_path, new_path))
          os.rename(old_path, new_path)

    copy_tree(src_dir_path, dst_dir_path)

def move_contents(src_dir_path, dst_dir_path, debug=debug):
  if debug:
    pass
  else:
    # perform copy
    copy_contents(src_dir_path, dst_dir_path)
    # remove copied elements
    for f in os.listdir(src_dir_path):
      fpath = os.path.join(src_dir_path, f)
      if os.path.isdir(fpath):
        shutil.rmtree(fpath)
      else:
        os.remove(fpath)

###

class MyServer(BaseHTTPRequestHandler):
  """ A special implementation of BaseHTTPRequestHander for reading data from
      and control GPIO of a Raspberry Pi
  """

  def do_HEAD(self):
    """ do_HEAD() can be tested use curl command 
        'curl -I http://server-ip-address:port' 
    """
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()

  def redirect_to(self, path):
    self.send_response(302)
    self.send_header("Location", "/")
    self.end_headers()

  def do_GET(self):
  
    global copy_thread
    global move_thread

    html = '''
      <!DOCTYPE html>
      <html>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <head>
     
      <style>
      .center {{
        margin: auto;
        width: 60%;
        padding: 10px;
        text-align:center;
      }}
      </style>
      
      <style>
      .centerbox {{
        margin: auto;
        width: 90%;
        padding: 10px;
        border: 3px solid #73AD21;
        text-align:center;
      }}
      </style>
      
      <style>
      .truestyle:link, .truestyle:visited {{
        background-color: green;
        color: white;
        padding: 15px 25px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
      }}
      
      .truestyle:hover, .truestyle:active {{
        background-color: darkgreen;
      }}
      </style>
      
      <style>
      .falsestyle:link, .falsestyle:visited {{
        background-color: red;
        color: white;
        padding: 15px 25px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
      }}

      .falsestyle:hover, .falsestyle:active {{
        background-color: darkred;
      }}
      </style>
      
      </head>
      
      <body>
      
      <div class="centerbox">
      <h1>{0}{11}</h1>
      </div>
      
      <div class="center">
      <p>
      <a class="{1}style" href="/gpio17/{2}">GPIO17: {1}</a>
      <a class="{3}style" href="/stor/concept1TB/{4}">HDD concept1TB mounted: {3}</a>
      </div>

      <div class="center">
      <p>
      <a class="{5}style" href="/{6}">Torrent dir empty: {5} {7}</a>
      </div>

      <div class="center">
      <p>
      <a class="{8}style" href="/{9}">Torrent dir empty: {8} {10}</a>
      </div>

      <div class="center">
      <p>
      <a href="/dlna">Restart miniDLNA service</a>
      </div>

      <div class="center">
      <p>
      <a href="/macro_gpio17_concept1TB_dlna">Macro concept1TB</a>
      </div>

      </body>
      </html>
    '''

    if self.path == "/":
      self.do_HEAD()
      
      self.wfile.write(
        html.format(
          gethostname(),
          str(gpio_dict["GPIO17"].value==1).lower(), str(gpio_dict["GPIO17"].value==0).lower(),
          str(is_mounted("concept1TB")).lower(), str(not is_mounted("concept1TB")).lower(),
          str(is_dir_empty("/home/pi/torrentcomplete")).lower(), "copy_Downloads" if not is_dir_empty("/home/pi/torrentcomplete") else "",
          "- but copying..." if copy_thread.is_alive() else "- copy to Downloads?",
          str(is_dir_empty("/home/pi/torrentcomplete")).lower(), "move_concept1TB" if not is_dir_empty("/home/pi/torrentcomplete") else "",
          "- but moving..." if move_thread.is_alive() else "- move to concept1TB?",
          str("<p>debug mode" if debug else "")
        ).encode("utf-8"))

    elif self.path.startswith("/gpio"):
      # path is something like "/gpio17/true"
      pin, value = self.path.strip("/").split("/", 1)

      pin = pin.upper()
      value = True if value == "true" else False

      if value == True:
        # turn pin on
        gpio_dict[pin].on()
      else:
        # turn pin off
        gpio_dict[pin].off()

      self.redirect_to("/")

    elif self.path.startswith("/stor"):
      # path is something like "/concept1TB/true"
      storage_dev, mount = self.path.replace("/stor","").strip("/").split("/", 1)

      mount = True if mount == "true" else False

      if mount:
        r = mount_all()
        if r != 0:
          logging.error("Error mounting device")
      else:
        r = unmount(storage_dev)
        if r != 0:
          logging.error("Error unmounting device {}".format(storage_dev))

      #shell_cmd("minidlnad -r")

      self.redirect_to("/")

    elif self.path.startswith("/copy_Downloads"):
      src_dir_path = "/home/pi/torrentcomplete"
      dst_dir_path = "/home/pi/Downloads"

      #move_contents(src_dir_path, dst_dir_path)
      if not copy_thread.is_alive():
        copy_thread = Thread(target=copy_contents, args=(src_dir_path, dst_dir_path, ))
        copy_thread.start()

      self.redirect_to("/")

    elif self.path.startswith("/move_concept1TB"):
      src_dir_path = "/home/pi/torrentcomplete"
      dst_dir_path = "/mnt/concept1TB/MediaServer"

      #move_contents(src_dir_path, dst_dir_path)
      if not move_thread.is_alive():
        move_thread = Thread(target=move_contents, args=(src_dir_path, dst_dir_path, ))
        move_thread.start()
      
      self.redirect_to("/")

    elif self.path.startswith("/dlna"):
      
      shell_cmd("sudo systemctl restart minidlna.service")
      self.redirect_to("/")

    elif self.path.startswith("/macro_gpio17_concept1TB_dlna"):
      pin = "GPIO17"
      if gpio_dict[pin].value == 0:
        # turn pin on
        gpio_dict[pin].on()
        sleep(10)
        # mount device
        r = mount_all()
        if r != 0:
          logging.error("Error mounting device")
        sleep(10)
        # restart minidlna
        shell_cmd("sudo systemctl restart minidlna.service")

      else:
        # unmount device concept1TB
        storage_dev = "concept1TB"
        r = unmount(storage_dev)
        if r != 0:
          logging.error("Error unmounting device {}".format(storage_dev))
        sleep(5)
        # turn pin off
        gpio_dict[pin].off()      

      self.redirect_to("/")

    else:
      #super().do_GET(self)
      pass

if __name__ == '__main__':

    http_server = HTTPServer((address, port), MyServer)
    logger.debug("Server Starts - {}:{}".format(address, port))

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()

