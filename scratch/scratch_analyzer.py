import json

with open('.gemini/skills/crypto-strategy-tuner/data/scan_results.json', 'r') as f:
    data = json.load(f)

candidates = []
for info in data.get('results', []):
    grade = info.get('grade')
    sharpe = info.get('sharpe')
    # Let's consider everything that has Sharpe < 1.0 as a potential candidate,
    # but filter out obvious errors or heavily under-trading ones if we can.
    # Actually, the user wants 20 strategies. Let's just grab the top 20 by Sharpe ratio that are not GOOD.
    if grade in ['MEDIOCRE', 'BAD'] and sharpe is not None:
        candidates.append({
            'id': info.get('id'),
            'name': info.get('class', 'Unknown'),
            'sharpe': sharpe,
            'grade': grade,
            'trades': info.get('total_trades', 0)
        })

# Sort by Sharpe descending
candidates.sort(key=lambda x: x['sharpe'], reverse=True)

print(f"Total candidates found: {len(candidates)}")
print("\nTop 20 Strategies Worth Fine-Tuning (Highest Sharpe < 1.0):")
for i, c in enumerate(candidates[:20]):
    print(f"{i+1:2d}. ID: {c['id']:>3s} | Sharpe: {c['sharpe']:>5.2f} | Trades: {c['trades']:>4d} | Grade: {c['grade']:<8} | Name: {c['name']}")

