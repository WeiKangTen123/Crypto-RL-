"""Auto-load every strategy file in this directory."""
import importlib.util as _ilu
import os as _os
import glob as _glob

_STRATEGY_DIR = _os.path.dirname(__file__)

for _fpath in _glob.glob(_os.path.join(_STRATEGY_DIR, '*.py')):
    _mod_name = _os.path.splitext(_os.path.basename(_fpath))[0]
    if _mod_name.startswith('_'):
        continue
    _spec = _ilu.spec_from_file_location(_mod_name, _fpath)
    _mod  = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    for _name in dir(_mod):
        if not _name.startswith('_'):
            globals()[_name] = getattr(_mod, _name)

from .avs_strategy import AVSStrategy

from .taker_intensity_breakout_strategy import TIPBreakoutStrategy
from .vegas_zscore_strategy import VegasZScoreStrategy
from .vegas_multicoin_portfolio_strategy import VegasMultiCoinPortfolioStrategy
