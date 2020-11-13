def raise_error(class_name, msg=""):
  try:
    raise NameError(class_name)
  except NameError:
    print(msg)
    raise