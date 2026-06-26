import os
import glob
import re

STRATEGY_DIR = "/Users/weikangten/Desktop/Crypto-RL/strategy_backtest/strategies"

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    orig = content

    pattern_long = re.compile(
        r"(\s*)if row\['is_bullish'\]:\s*"
        r"\1    if (?:float\()?row\['High'\](?:\))? >= (.+?): return 'TP', \2\s*"
        r"\1    if (?:float\()?row\['Low'\](?:\))?\s*<= (.+?): return 'SL', \3\s*"
        r"\1else:\s*"
        r"\1    if (?:float\()?row\['Low'\](?:\))?\s*<= \3: return 'SL', \3\s*"
        r"\1    if (?:float\()?row\['High'\](?:\))? >= \2: return 'TP', \2"
    )
    
    def repl_long(match):
        indent = match.group(1)
        tp = match.group(2)
        sl = match.group(3)
        return f"{indent}if float(row['Low'])  <= {sl}: return 'SL', {sl}\n{indent}if float(row['High']) >= {tp}: return 'TP', {tp}"

    pattern_short = re.compile(
        r"(\s*)if row\['is_bullish'\]:\s*"
        r"\1    if (?:float\()?row\['High'\](?:\))? >= (.+?): return 'SL', \2\s*"
        r"\1    if (?:float\()?row\['Low'\](?:\))?\s*<= (.+?): return 'TP', \3\s*"
        r"\1else:\s*"
        r"\1    if (?:float\()?row\['Low'\](?:\))?\s*<= \3: return 'TP', \3\s*"
        r"\1    if (?:float\()?row\['High'\](?:\))? >= \2: return 'SL', \2"
    )

    def repl_short(match):
        indent = match.group(1)
        sl = match.group(2)
        tp = match.group(3)
        return f"{indent}if float(row['High']) >= {sl}: return 'SL', {sl}\n{indent}if float(row['Low'])  <= {tp}: return 'TP', {tp}"

    content = pattern_long.sub(repl_long, content)
    content = pattern_short.sub(repl_short, content)

    if content != orig:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    files = glob.glob(os.path.join(STRATEGY_DIR, "*.py"))
    modified_count = 0
    for file in files:
        if process_file(file):
            modified_count += 1
            print(f"Modified: {os.path.basename(file)}")
            
    print(f"\nTotal files modified: {modified_count}")

if __name__ == '__main__':
    main()
