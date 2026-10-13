#!/usr/bin/env python3
"""Run the plugin's cost report from inside the skill.

The report itself is `runtime/report.py`, beside the hook that fills the ledger it reads. This
file only finds it, from its own resolved location, so the skill works when its directory is
reached through a symbolic link.
"""

import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
runpy.run_path(str(Path(__file__).resolve().parents[3] / "runtime" / "report.py"), run_name="__main__")
