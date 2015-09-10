import sys
import os.path

crr_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, crr_path)
from GeoCoding import app as application