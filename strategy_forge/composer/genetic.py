"""
genetic.py — genetic algorithm to evolve StrategyDNA populations.

Flow:
  1. Score population via backtest
  2. Select top survivors
  3. Crossover pairs → child DNA
  4. Mutate children randomly
  5. Repeat for N generations
"""
import random
from typing import List, Tuple, Callable

from strategy_forge.composer.dna           import StrategyDNA
from strategy_forge.composer.random_compose import random_dna, _ENTRY_PARAMS, _FILTER_PARAMS, _EXIT_PARAMS
from strategy_forge.params.ranges           import DEFAULT_RANGES, sample_params
from strategy_forge.signals.entry_signals   import ENTRY_SIGNAL_REGISTRY
from strategy_forge.signals.filter_signals  import FILTER_REGISTRY
from strategy_forge.signals.exit_signals    import EXIT_REGISTRY


def crossover(parent_a: StrategyDNA, parent_b: StrategyDNA,
              df, rng: random.Random) -> StrategyDNA:
    """
    Produce one child by mixing parents.
    - entry / exit : randomly chosen from either parent
    - filters      : union of both parents' filters, trimmed to max 2
    - params       : per-key, randomly pick from either parent
    """
    child_entry  = rng.choice([parent_a.entry, parent_b.entry])
    child_exit   = rng.choice([parent_a.exit_method, parent_b.exit_method])

    combined_filters = list(set(parent_a.filters + parent_b.filters))
    rng.shuffle(combined_filters)
    child_filters = combined_filters[:2]   # cap at 2

    # Merge params: for each key in either parent, pick from one randomly
    all_keys = set(parent_a.params) | set(parent_b.params)
    child_params = {}
    for k in all_keys:
        a_val = parent_a.params.get(k)
        b_val = parent_b.params.get(k)
        if a_val is None:
            child_params[k] = b_val
        elif b_val is None:
            child_params[k] = a_val
        else:
            child_params[k] = rng.choice([a_val, b_val])

    return StrategyDNA(df, entry=child_entry, filters=child_filters,
                       exit_method=child_exit, params=child_params)


def mutate(dna: StrategyDNA, df, rng: random.Random,
           mutation_rate: float = 0.2) -> StrategyDNA:
    """
    Randomly mutate a StrategyDNA:
    - With prob mutation_rate, swap entry/exit/a filter
    - With prob mutation_rate per param, resample that param
    """
    entry  = dna.entry
    exit_m = dna.exit_method
    fltrs  = list(dna.filters)
    params = dict(dna.params)

    if rng.random() < mutation_rate:
        entry = rng.choice(list(ENTRY_SIGNAL_REGISTRY.keys()))
    if rng.random() < mutation_rate:
        exit_m = rng.choice(list(EXIT_REGISTRY.keys()))
    if fltrs and rng.random() < mutation_rate:
        idx = rng.randint(0, len(fltrs) - 1)
        fltrs[idx] = rng.choice(list(FILTER_REGISTRY.keys()))

    for k, v in params.items():
        if rng.random() < mutation_rate and k in DEFAULT_RANGES:
            lo, hi = DEFAULT_RANGES[k]
            if isinstance(lo, int) and isinstance(hi, int):
                params[k] = rng.randint(lo, hi)
            else:
                params[k] = round(rng.uniform(float(lo), float(hi)), 4)

    # Fix fast/slow constraints after mutation
    for fast_k, slow_k, gap in [
        ('ema_fast',  'ema_slow',  5),
        ('macd_fast', 'macd_slow', 5),
        ('hma_fast',  'hma_slow',  5),
    ]:
        if fast_k in params and slow_k in params:
            if params[fast_k] >= params[slow_k]:
                params[fast_k] = max(3, params[slow_k] - gap)
    if 'wt_n1' in params and 'wt_n2' in params:
        if params['wt_n1'] >= params['wt_n2']:
            params['wt_n1'] = max(3, params['wt_n2'] - 3)

    return StrategyDNA(df, entry=entry, filters=fltrs, exit_method=exit_m, params=params)


def evolve(population: List[Tuple[float, StrategyDNA]],
           df,
           n_survivors: int = 10,
           n_offspring: int = 30,
           mutation_rate: float = 0.2,
           seed: int = None) -> List[StrategyDNA]:
    """
    One generation of evolution.

    Parameters
    ----------
    population  : list of (score, StrategyDNA) sorted descending by score
    df          : OHLCV DataFrame for new children
    n_survivors : top-N kept from current generation
    n_offspring : number of children to generate
    mutation_rate : probability of mutating each gene

    Returns
    -------
    New population as list of StrategyDNA (unscored, ready for backtest).
    """
    rng = random.Random(seed)

    # Keep top survivors as-is
    survivors = [dna for _, dna in population[:n_survivors]]

    children = []
    for _ in range(n_offspring):
        pa, pb = rng.sample(survivors, k=min(2, len(survivors)))
        child  = crossover(pa, pb, df, rng)
        child  = mutate(child, df, rng, mutation_rate)
        children.append(child)

    # Fill remaining slots with fresh random individuals (diversity injection)
    n_random = max(0, n_offspring - len(children))
    fresh = [random_dna(df, seed=rng.randint(0, 2**31)) for _ in range(n_random)]

    return survivors + children + fresh
