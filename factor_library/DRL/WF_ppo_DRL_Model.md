---
autopsy_report: phase_6_agent_monitor/alpha_forge_v2/autopsy_report/20260614_res_2026-06-11__10_10_54_model_WF_ppo_4h_50H_15k_WF_ppo_autopsy.md
name: Walk Forward PPO Deep Reinforcement Learning Model
rejection_reason: PBO Audit Failure - study.pkl contained no completed trials.
status: REJECTED
strategy_id: WF_ppo_DRL_Model
tags:
- rejected
---
# WF_ppo Deep Reinforcement Learning Model

This card describes the `WF_ppo` DRL model which underwent a PBO (Probability of Backtest Overfitting) audit.

## Status

**REJECTED**

**Reason for Rejection:** The PBO audit failed due to an inability to load completed trials from the associated `study.pkl` file. This indicates a potential issue during the model's optimization phase, leading to an incomplete or corrupted dataset for PBO analysis.

## Details

**Model Identifier:** `res_2026-06-11__10_10_54_model_WF_ppo_4h_50H_15k`
**Failure Stage:** Stage 7 (PBO_AUDIT)
**Autopsy Report:** [Link to Autopsy Report](phase_6_agent_monitor/alpha_forge_v2/autopsy_report/20260614_res_2026-06-11__10_10_54_model_WF_ppo_4h_50H_15k_WF_ppo_autopsy.md)

## Next Steps

This model is considered "Poison" and should not be used. Further investigation into the DRL training pipeline and Optuna study saving mechanism is recommended before attempting to re-evaluate this or similar models.
