import os
import json
from pymud.pymud import *

cfg = "pymud.cfg"
with open(cfg, "r", encoding="utf8", errors="ignore") as fp:
    cfg_data = json.load(fp)
    app = PyMudApp(cfg_data)
    app.run()