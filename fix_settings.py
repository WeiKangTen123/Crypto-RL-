import sys

file_path = "strategy_backtest/settings.py"
with open(file_path, "r") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if line.strip() == '"159": {':
        start_idx = i
    if start_idx != -1 and line.strip() == '"178": {':
        pass # found 178
    if start_idx != -1 and line.strip() == '"FORGE_EMA_MACD_XRP_1D",':
        pass
        
# Find the exact end of 178.
# 178 starts around 1708. We find the matching closing brace.
for i in range(start_idx, len(lines)):
    if 'FORGE_EMA_MACD_XRP_1D' in lines[i]:
        # Now find the next "    },"
        for j in range(i, len(lines)):
            if lines[j].startswith("    },"):
                end_idx = j
                break
        break

if start_idx != -1 and end_idx != -1:
    print(f"Removing lines {start_idx} to {end_idx}")
    del lines[start_idx:end_idx+1]
    
    # Check if 82 is closed. 
    # Since we inserted between 82's params closing `    },` and its strategy closing `    },`
    # No, wait, 82's params closed at 1308. But maybe 82 didn't have a closing `    },` because my previous script overrode it?
    # Let's just write the fixed content to a temp file and inspect.
    with open("strategy_backtest/settings.tmp.py", "w") as f:
        f.writelines(lines)
    print("Wrote to settings.tmp.py")
else:
    print("Could not find bounds.")
