import os, sys
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(project_root)
from app_sobral_invest import debug_log

debug_log("Test debug entry")
print("Debug entry written.")
