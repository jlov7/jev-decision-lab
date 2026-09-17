"""Rebuild authored datasets and bibliography. Offline; no package installation."""
import runpy
from pathlib import Path
root = Path(__file__).resolve().parents[1]
(root/'data').mkdir(exist_ok=True)
(root/'docs').mkdir(exist_ok=True)
for name in ('seed_cases.py', 'seed_signals.py', 'source_register.py'):
    runpy.run_path(str(root/'scripts'/name), run_name='__main__')
print('Authored datasets and bibliography rebuilt. No network or model calls.')
