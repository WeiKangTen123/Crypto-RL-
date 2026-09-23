import json

with open('.gemini/skills/crypto-strategy-tuner/data/scan_results.json', 'r') as f:
    data = json.load(f)

candidates = []
for info in data.get('results', []):
    grade = info.get('grade')
    sharpe = info.get('sharpe')
    total_return = info.get('total_return')
    max_drawdown = info.get('max_drawdown')
    
    if sharpe is not None and total_return is not None and max_drawdown is not None:
        # Looking for terrible performers: Negative ROI or massive drawdown (liquidated)
        if total_return < 0 or max_drawdown > 80:
            candidates.append({
                'id': info.get('id'),
                'name': info.get('class', 'Unknown'),
                'sharpe': sharpe,
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'trades': info.get('total_trades', 0)
            })

# Sort by worst Total Return ascending (most negative first)
candidates.sort(key=lambda x: x['total_return'])

print(f"Total terrible candidates found: {len(candidates)}")
print("\nTop 20 Worst Strategies Worth Salvaging (Deep Negative ROI / Liquidations):")
print(f"{'#':<3} | {'ID':<3} | {'Sharpe':>7} | {'Return %':>9} | {'MaxDD %':>7} | {'Trades':>6} | {'Name'}")
print("-" * 80)
for i, c in enumerate(candidates[:20]):
    print(f"{i+1:<3} | {c['id']:<3} | {c['sharpe']:>7.2f} | {c['total_return']:>9.2f} | {c['max_drawdown']:>7.2f} | {c['trades']:>6d} | {c['name']}")

