import sys, os, json
from .pymud import main

if __name__ == "__main__":
    cfg = "pymud.cfg"

    args = sys.argv
    if len(args) > 1:
        cfg = args[1]

    if os.path.exists(cfg):
        with open(cfg, "r", encoding="utf8", errors="ignore") as fp:
            cfg_data = json.load(fp)
            main(cfg_data)
    else:
        main()