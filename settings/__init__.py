try:
    from .local_settings import *
except ImportError:
    print ("INFO: No local_settings.py found, please create one to overwrite the default settings!"
           "INFO: \n"
           "INFO:         An example of an local_settings.py file is: \n"
           "INFO:         '''\n"
           "INFO:         local_settings_example.py *\n"
           "INFO:         '''\n")
