import sys; sys.path.insert(0, '.')
import phase_10.engine as eng

DATASET = 'dataset'
DATE_FROM, DATE_TO = '2023-01-01', '2026-05-31'
PAIRS = eng.PAIRS

configs = [
    ('I  baseline   ', 120, 48, 2.5, 5.0, 0.80,  6, True),
    ('P  stop_6.0   ', 120, 48, 2.5, 6.0, 0.80,  6, True),
    ('Q  stop_7.0   ', 120, 48, 2.5, 7.0, 0.80,  6, True),
    ('R  minz_2.0   ', 120, 48, 2.0, 5.0, 0.80,  6, True),
    ('S  minz_3.0   ', 120, 48, 3.0, 5.0, 0.80,  6, True),
    ('T  ols_100    ', 100, 40, 2.5, 5.0, 0.80,  6, True),
    ('U  ols_144    ', 144, 54, 2.5, 5.0, 0.80,  6, True),
    ('V  cd_24      ', 120, 48, 2.5, 5.0, 0.80, 24, True),
    ('W  z2_s6_cd12 ', 120, 48, 2.0, 6.0, 0.80, 12, True),
    ('X  z3_s6_r85  ', 120, 48, 3.0, 6.0, 0.85,  6, True),
]

print('Config             |     ROI%    Shrp   Trds    WR%   ZSt%    MR%')
print('-' * 72)
sys.stdout.flush()

for label, ols, zscore, min_z, stop, min_r2, cooldown, confirm in configs:
    eng.OLS_WINDOW=ols; eng.ZSCORE_WINDOW=zscore; eng.MIN_ENTRY_Z=min_z
    eng.Z_STOP_LOSS=stop; eng.MAX_ENTRY_Z=stop-0.10; eng.MIN_R2=min_r2
    eng.COOLDOWN_BARS=cooldown; eng.CONFIRM_TURN=confirm
    tr=0; ts=0; wr=0; zs=0; mr=0; n=0
    for a, b in PAIRS:
        try:
            r = eng.run_pair_backtest(a, b, DATASET,
                date_from=DATE_FROM, date_to=DATE_TO, timeframe='1h')
            if r.get('error') or r['total_trades'] == 0:
                continue
            tr += r['roi']; ts += r['sharpe']; wr += r['win_rate']
            zs += r['exit_zstop_pct']; mr += r['exit_mr_pct']; n += 1
        except Exception as e:
            print(f'  ERROR {a}-{b}: {e}', flush=True)
    if n == 0:
        print(f'{label} | no trades', flush=True)
        continue
    print(f'{label} | {tr:>+8.1f} {ts/n:>+7.3f} {wr/n:>6.1f}% {zs/n:>6.1f}% {mr/n:>6.1f}%', flush=True)
