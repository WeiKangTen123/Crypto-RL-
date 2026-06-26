import os
import pandas as pd
import yaml
import re

def update_factor_card(file_path, results_row):
    """
    Updates the YAML frontmatter and the Performance Summary table in a factor card.
    Status auto-update rules (only applies to transitional states QUEUED/HANDED_OFF/IN_PROGRESS):
      - sharpe > 1.0  → VALIDATED
      - sharpe < 0.0  → REJECTED
      - otherwise     → IN_PROGRESS
    Developer-set VALIDATED/REJECTED are never overridden.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split frontmatter and body
    parts = re.split(r'^---$', content, flags=re.MULTILINE)
    if len(parts) < 3:
        print(f"  [WARN] {file_path} does not have valid YAML frontmatter.")
        return False

    fm_raw = parts[1]
    body = parts[2]

    try:
        fm = yaml.safe_load(fm_raw)
    except Exception as e:
        print(f"  [ERROR] Parsing YAML in {file_path}: {e}")
        return False

    # Update performance metrics in frontmatter
    sharpe       = float(results_row.get('Sharpe Ratio', 0.0))
    win_rate     = float(results_row.get('Win Rate', 0.0))
    total_return = float(results_row.get('Total Return', 0.0))
    max_drawdown = float(results_row.get('Max Drawdown %', 0.0))

    fm['sharpe']       = round(sharpe, 2)
    fm['win_rate']     = round(win_rate, 2)
    fm['total_return'] = round(total_return, 2)
    fm['max_drawdown'] = round(max_drawdown, 2)

    # Auto-update status only for transitional states — never override a manual VALIDATED/REJECTED
    auto_update_statuses = {'QUEUED', 'HANDED_OFF', 'IN_PROGRESS'}
    if fm.get('status') in auto_update_statuses:
        if sharpe > 1.0:
            fm['status'] = 'VALIDATED'
        elif sharpe < 0.0:
            fm['status'] = 'REJECTED'
        else:
            fm['status'] = 'IN_PROGRESS'

    new_fm_raw = yaml.dump(fm, sort_keys=False, default_flow_style=False)

    # Update Performance Summary table in body
    table_pattern = (
        r'## Performance Summary.*?\n'
        r'\| Metric \| Value \|\n'
        r'\| --- \| --- \|\n'
        r'\| Sharpe Ratio \| .*? \|\n'
        r'\| Win Rate \| .*? \|\n'
        r'\| Total Return \| .*? \|\n'
        r'\| Max Drawdown \| .*? \|'
    )

    new_table = (
        f"## Performance Summary\n"
        f"*Auto-updated by sync_backtest_to_obsidian.py when strategy_id matches.*\n\n"
        f"| Metric | Value |\n"
        f"| --- | --- |\n"
        f"| Sharpe Ratio | {fm['sharpe']} |\n"
        f"| Win Rate | {fm['win_rate']}% |\n"
        f"| Total Return | {fm['total_return']}% |\n"
        f"| Max Drawdown | {fm['max_drawdown']}% |"
    )

    if re.search(table_pattern, body, re.DOTALL):
        new_body = re.sub(table_pattern, new_table, body, flags=re.DOTALL)
    else:
        new_body = body + "\n\n" + new_table

    new_content = f"---{new_fm_raw}---{new_body}"

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True

def main():
    results_path = 'results/technical_backtest.csv'
    factor_dir = 'factor_library'

    if not os.path.exists(results_path):
        print(f"[ERROR] Results file not found: {results_path}")
        return

    results_df = pd.read_csv(results_path)

    # Create a mapping of strategy_id to row
    results_map = results_df.set_index('strategy_id').to_dict('index')

    updated_count = 0
    for root, dirs, files in os.walk(factor_dir):
        for file in files:
            if file.endswith('.md') and file != 'README.md' and not file.startswith('_Index'):
                file_path = os.path.join(root, file)

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for strategy_id in YAML
                fm_match = re.search(r'^---(.*?)---', content, re.DOTALL | re.MULTILINE)
                if fm_match:
                    try:
                        fm = yaml.safe_load(fm_match.group(1))
                        sid = fm.get('strategy_id')

                        if sid and sid != 'TBD' and sid in results_map:
                            print(f"[INFO] Updating {file_path} for strategy {sid}")
                            if update_factor_card(file_path, results_map[sid]):
                                updated_count += 1
                    except Exception:
                        continue

    print(f"\n[FINISH] Updated {updated_count} factor cards.")

if __name__ == '__main__':
    main()
