#!/usr/bin/python

import sys
import slp

def srvc_types_callback(h, srvc_type, errcode, cookie_data):
      _discovered_service_types_list = []
      # global count
      rv = False
      if errcode == slp.SLP_OK:
        print(srvc_type)
        # count += 1
        rv = True
      elif errcode == slp.SLP_LAST_CALL:
        # if count == 0:
        #   print(rqst_type + ": Nothing found")
        # else:
        #   print("Found " + str(count) + " " + rqst_type)
        pass # TODO G: fix count
      else:
        print("Error: " + str(errcode))
      
      if rv == True:
        _discovered_service_types_list.append(srvc_type)
      return rv

def service_callback(h, srvurl, lifetime, errcode, data):
    global count
    rv = False
    if errcode == slp.SLP_OK:
        print("Url: " + srvurl + ", timeout " + str(lifetime))
        print(slp.SLPParseSrvURL(srvurl))
        count += 1
        rv = True
    elif errcode == slp.SLP_LAST_CALL:
        if count == 0:
            print("Services: Nothing found")
        else:
            print("Found " + str(count) + " services")
    else:
        print("Error: " + str(errcode))
    return rv

def attr_callback(h, attrlist, errcode, data):
    global count
    rv = False
    if errcode == slp.SLP_OK:
        print("Attrs: " + attrlist)
        count += 1
        rv = True
    elif errcode == slp.SLP_LAST_CALL:
        if count == 0:
            print("Attrs: Nothing found")
        else:
            print("Found " + str(count) + " attribute lists")
    else:
        print("Error: " + str(errcode))
    return rv

def reg_callback(h, errcode, data):
    if errcode != slp.SLP_OK:
        print("Error registering service: " + str(errcode))
    return None

############

# if len(sys.argv) < 2:
#     sys.exit('Usage: %s <service url>' % sys.argv[0])

# url = sys.argv[1];

url = "service:ciao"

############

try:
    hslp = slp.SLPOpen("en", False)
except RuntimeError as e:
    print("Error opening the SLP handle: " + str(e))
    sys.exit("Giving up")

############

count = 0;
try:
    slp.SLPFindSrvTypes(hslp, "*", "", srvc_types_callback, None)
except RuntimeError as e:
    print("Error discovering the service: " + str(e))

count = 0;
try:
    slp.SLPFindSrvs(hslp, url, None, None, service_callback, None)
except RuntimeError as e:
    print("Error discovering the service: " + str(e))

count = 0;
try:
    slp.SLPFindAttrs(hslp, url, None, None, attr_callback, None);
except RuntimeError as e:
    print("Error discovering the service attributes: " + str(e))

############

testSrvUrl = "service:nothing"
testSrvHost = "://127.0.0.1"

print("Testing registration of " + testSrvUrl + " with lifetime " + str(slp.SLP_LIFETIME_DEFAULT))

try:
    slp.SLPReg(hslp, testSrvUrl + testSrvHost, slp.SLP_LIFETIME_DEFAULT, None,
        "(desc=test)", True, reg_callback, None)
except RuntimeError as e:
    print("Error registering new service: " + str(e))

count = 0;
try:
    slp.SLPFindSrvTypes(hslp, "*", "", srvc_types_callback, None)
except RuntimeError as e:
    print("Error discovering the service: " + str(e))

count = 0;
try:
    slp.SLPFindSrvs(hslp, testSrvUrl, None, None, service_callback, None)
except RuntimeError as e:
    print("Error discovering the service: " + str(e))

if count == 0:
    print("Could not find the registered service!")

count = 0;
try:
    slp.SLPFindAttrs(hslp, testSrvUrl, None, None, attr_callback, None)
except RuntimeError as e:
    print("Error discovering the service attributes: " + str(e))

if count == 0:
    print("Could not find the registered service attributes!")

############

slp.SLPClose(hslp);
