#!/bin/bash
python .gemini/skills/crypto-strategy-tuner/scripts/finetune.py --strategy_id 145
python .gemini/skills/crypto-strategy-tuner/scripts/finetune.py --strategy_id 146
python .gemini/skills/crypto-strategy-tuner/scripts/finetune.py --strategy_id 147
python .gemini/skills/crypto-strategy-tuner/scripts/scan_all.py
