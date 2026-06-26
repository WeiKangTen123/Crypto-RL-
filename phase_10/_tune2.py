import sys; sys.path.insert(0, '.')
import phase_10.engine as eng

DATASET = 'dataset'
DATE_FROM, DATE_TO = '2023-01-01', '2026-05-31'
PAIRS = eng.PAIRS

# Lock in Q params, vary hold + stop
eng.OLS_WINDOW=120; eng.ZSCORE_WINDOW=48; eng.MIN_ENTRY_Z=2.5
eng.MIN_R2=0.80; eng.COOLDOWN_BARS=6; eng.CONFIRM_TURN=True

configs = [
    ('Q  s7.0 HL    ', 7.0, None),
    ('Q1 s7.0 24h   ', 7.0,  24),
    ('Q2 s7.0 48h   ', 7.0,  48),
    ('Q3 s7.0 72h   ', 7.0,  72),
    ('Q4 s7.0 168h  ', 7.0, 168),
    ('Q5 s7.0 336h  ', 7.0, 336),
    ('Z1 s8.0 HL    ', 8.0, None),
    ('Z2 s9.0 HL    ', 9.0, None),
    ('Z3 s10  HL    ',10.0, None),
    ('Z4 s8.0 168h  ', 8.0, 168),
]

print('Config             |     ROI%    Shrp   Trds    WR%   ZSt%    MR%    TS%')
print('-' * 75)
for label, stop, hold_h in configs:
    eng.Z_STOP_LOSS = stop
    eng.MAX_ENTRY_Z = stop - 0.10
    tr=0; ts=0; wr=0; zs=0; mr=0; tsp=0; n=0
    for a, b in PAIRS:
        try:
            r = eng.run_pair_backtest(a, b, DATASET,
                date_from=DATE_FROM, date_to=DATE_TO, timeframe='1h',
                max_hold_override=hold_h)
            if r.get('error') or r['total_trades'] == 0: continue
            tr += r['roi']; ts += r['sharpe']; wr += r['win_rate']
            zs += r['exit_zstop_pct']; mr += r['exit_mr_pct']
            tsp += r['exit_ts_pct']; n += 1
        except Exception as e:
            print(f'  ERR {a}-{b}: {e}', flush=True)
    if n == 0:
        print(f'{label} | no trades'); continue
    print(f'{label} | {tr:>+8.1f} {ts/n:>+7.3f} {wr/n:>6.1f}% {zs/n:>5.1f}% {mr/n:>6.1f}% {tsp/n:>5.1f}%', flush=True)
