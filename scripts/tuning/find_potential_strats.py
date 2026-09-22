import json

def analyze_bad_strategies():
    with open('.gemini/skills/crypto-strategy-tuner/data/scan_results.json', 'r') as f:
        data = json.load(f)

    bads = [r for r in data.get('results', []) if r.get('grade') == 'BAD']
    
    print(f"Total BAD strategies: {len(bads)}")
    
    # Let's define potential:
    # A bad strategy could be fine-tuned if:
    # 1. It actually has a positive Sharpe ratio, but was classified as BAD (e.g., drawdown > 20, or low trades)
    # 2. It has a high Sharpe ratio but is negative (maybe we can invert it?) -> Sharpe < -1.0 with many trades
    # 3. Very high number of trades with a sharpe close to 0 (maybe edge is hidden by fees, parameters can be tuned)
    
    potential = []
    for r in bads:
        sharpe = r.get('sharpe', -999)
        trades = r.get('total_trades', 0)
        drawdown = r.get('max_drawdown', 100)
        ret = r.get('total_return', -100)
        name = r.get('class', 'Unknown')
        sid = r.get('id')
        
        # Calculate a "potential score". Higher is better.
        # Examples of good potential:
        # - Positive sharpe
        # - Decent return but high drawdown (needs risk management)
        # - High trades
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
            reasons.append(f"Statistically Significant ({trades} trades)")
            
        if sharpe < -1.5 and trades > 100:
            score += abs(sharpe) * 30
            reasons.append("Consistently Bad (Invertible?)")
            
        # Give points if drawdown is relatively low for a "BAD" strategy (< 50%)
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
    
    print("\nTop 15 BAD Strategies with High Potential for Fine-Tuning:")
    print(f"{'ID':<4} | {'Name':<35} | {'Sharpe':>7} | {'Ret %':>7} | {'DD %':>6} | {'Trades':>6} | {'Score':>6} | {'Reasons'}")
    print("-" * 120)
    for p in potential[:15]:
        print(f"{p['id']:<4} | {p['name']:<35} | {p['sharpe']:>7.2f} | {p['ret']:>7.2f} | {p['drawdown']:>6.2f} | {p['trades']:>6} | {p['score']:>6.1f} | {p['reasons']}")

if __name__ == '__main__':
    analyze_bad_strategies()
