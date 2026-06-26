import os
import glob
import re

STRATEGY_DIR = "/Users/weikangten/Desktop/Crypto-RL/strategy_backtest/strategies"

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    i = 0
    modified = False
    
    while i < len(lines):
        line = lines[i]
        
        # Look for the start of the if row['is_bullish']: block
        if "if row['is_bullish']:" in line:
            indent = line[:line.find("if row['is_bullish']:")]
            
            # Check if this is a standard 5-line block:
            # if row['is_bullish']:
            #     line 1
            #     line 2
            # else:
            #     line 3
            #     line 4
            if i + 5 < len(lines) and lines[i+3].strip() == "else:":
                if_block = [lines[i+1], lines[i+2]]
                else_block = [lines[i+4], lines[i+5]]
                
                # Determine which one is pessimistic (starts with SL)
                # For Long, SL check uses 'Low'
                # For Short, SL check uses 'High'
                
                # Let's just find which block checks SL first
                if "'SL'" in if_block[0]:
                    pessimistic_block = if_block
                elif "'SL'" in else_block[0]:
                    pessimistic_block = else_block
                else:
                    # Fallback if we can't tell, just leave it alone
                    new_lines.append(line)
                    i += 1
                    continue
                    
                # Fix indentation for the selected block (it has one extra level of indentation)
                fixed_block = []
                for b_line in pessimistic_block:
                    # Remove 4 spaces of indentation
                    if b_line.startswith(indent + "    "):
                        fixed_block.append(indent + b_line[len(indent) + 4:])
                    else:
                        fixed_block.append(b_line)
                        
                new_lines.extend(fixed_block)
                i += 6 # Skip the 5 lines of the if/else block + the first line
                modified = True
                continue
                
        new_lines.append(line)
        i += 1
        
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
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
