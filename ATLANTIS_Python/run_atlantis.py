"""Launch ATLANTIS. A project-local development dependency folder is optional."""
from pathlib import Path
import sys
local=Path(__file__).parent/'.deps'
if local.exists(): sys.path.insert(0,str(local))
from atlantis.gui import main
raise SystemExit(main())
