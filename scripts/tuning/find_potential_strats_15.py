import json

def analyze_bad_strategies():
    with open('.gemini/skills/crypto-strategy-tuner/data/scan_results.json', 'r') as f:
        data = json.load(f)

    bads = [r for r in data.get('results', []) if r.get('grade') == 'BAD']
    
    # Exclude already tuned
    tuned = ['20', '196', '1', '242', '184', '11', '135', '87', '150', '203']
    # And we want to exclude the "consistently bad" ones that need logic inversion, wait, I can just exclude the ones I listed as invertible: 159, 112, 164
    invertible = ['159', '112', '164']
    exclude = set(tuned + invertible)
    
    potential = []
    for r in bads:
        sharpe = r.get('sharpe', -999)
        trades = r.get('total_trades', 0)
        drawdown = r.get('max_drawdown', 100)
        ret = r.get('total_return', -100)
        name = r.get('class', 'Unknown')
        sid = str(r.get('id'))
        
        if sid in exclude:
            continue
            
        score = 0
        reasons = []
        
        if sharpe > 0:
            score += sharpe * 50
            reasons.append("Positive Sharpe")
        
        if ret > 0:
            score += 20
            reasons.append("Positive Return")
            
        if trades > 100:
            score += 10
            reasons.append(f"Sig ({trades} trades)")
            
        if drawdown < 50:
            score += (50 - drawdown)
            reasons.append(f"Manageable DD ({drawdown:.1f}%)")
            
        if score > 0:
            potential.append({
                'id': sid,
                'name': name,
                'sharpe': sharpe,
                'ret': ret,
                'drawdown': drawdown,
                'trades': trades,
                'score': score,
                'reasons': ", ".join(reasons)
            })

    potential.sort(key=lambda x: x['score'], reverse=True)
    
    print("\nNext 15 BAD Strategies with High Potential for Fine-Tuning:")
    print(f"{'ID':<4} | {'Name':<35} | {'Sharpe':>7} | {'Ret %':>7} | {'DD %':>6} | {'Trades':>6} | {'Score':>6} | {'Reasons'}")
    print("-" * 120)
    
    targets = []
    for p in potential[:15]:
        print(f"{p['id']:<4} | {p['name']:<35} | {p['sharpe']:>7.2f} | {p['ret']:>7.2f} | {p['drawdown']:>6.2f} | {p['trades']:>6} | {p['score']:>6.1f} | {p['reasons']}")
        targets.append(p['id'])
        
    print("\nTARGETS = " + repr(targets))

if __name__ == '__main__':
    analyze_bad_strategies()
