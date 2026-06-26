#!/bin/bash
for i in {164..170}; do
    echo "Starting tuning for ID $i with 400 trials..."
    python .gemini/skills/crypto-strategy-tuner/scripts/finetune.py --strategy_id $i --trials 400
done
