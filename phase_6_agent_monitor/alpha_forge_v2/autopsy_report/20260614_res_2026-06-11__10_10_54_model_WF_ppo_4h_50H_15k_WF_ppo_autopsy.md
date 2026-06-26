# Autopsy Report: WF_ppo Strategy Failure

**Date:** 2026-06-14
**Strategy ID:** res_2026-06-11__10_10_54_model_WF_ppo_4h_50H_15k
**Strategy Name:** WF_ppo

**Stage of Failure:** PBO_AUDIT (Stage 7)

**Exact Error Message:**
```
Error finding best trial for res_2026-06-11__10_10_54_model_WF_ppo_4h_50H_15k: No trials are completed yet.
Error loading res_2026-06-11__10_10_54_model_WF_ppo_4h_50H_15k: No valid trials completed
```

**Parameters at time of crash:**
- `pickle_result` argument for `pbo.py`: `res_2026-06-11__10_10_54_model_WF_ppo_4h_50H_15k`

**Root Cause Diagnosis:**
The `study.pkl` file located in `train_results/res_2026-06-11__10_10_54_model_WF_ppo_4h_50H_15k/` does not contain any completed Optuna trials. This prevents the PBO analysis (which relies on completed trials and their `user_attrs`) from proceeding. The likely cause is an interrupted optimization process or an issue during the saving of the Optuna study, leading to an incomplete or corrupted study file.

**Verdict:**
Strategy `WF_ppo` (ID: `res_2026-06-11__10_10_54_model_WF_ppo_4h_50H_15k`) is **REJECTED** at Stage 7 (PBO_AUDIT) due to an unrecoverable error in loading optimization results. It is considered "Poison" and should not be used in future strategies without structural refactoring and a successful re-run of the entire 8-stage pipeline.