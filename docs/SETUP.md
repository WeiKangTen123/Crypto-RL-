Step 1 — Install dependencies (one time only):


cd /Users/weikangten/Desktop/Crypto-RL
./venv/bin/pip install -r requirements.txt
Step 2 — Process train + validation data:


./venv/bin/python phase_0/dl_trainval_data.py
Reads your parquet files, computes TA-Lib indicators, saves arrays to data/ folder.

Step 3 — Process test/trade data:


./venv/bin/python phase_0/dl_trade_data.py
Same thing but for the 2024-07 → 2026-04 test window.

Step 4 — Hyperparameter optimisation (pick one):


./venv/bin/python phase_1/optimize_cpcv.py   # recommended (most rigorous)
# or
./venv/bin/python phase_1/optimize_kcv.py
# or
./venv/bin/python phase_1/optimize_wf.py
Runs Optuna + CPCV cross-validation. Takes the longest — controlled by H_TRIALS = 50 in config.

Step 5 — Validate:


./venv/bin/python phase_2/validate.py
Step 6 — Backtest:


./venv/bin/python phase_4/backtest.py
Step 7 — PBO analysis:


./venv/bin/python phase_5/pbo.py