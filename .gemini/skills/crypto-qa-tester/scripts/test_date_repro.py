import pandas as pd

def _safe_date(d, default):
    try:
        if not d or str(d).lower() == 'invalid-date':
            return default
        pd.Timestamp(d)
        return str(d)
    except Exception:
        return default

print(f"Result for 'invalid-date': {_safe_date('invalid-date', 'DEFAULT')}")
print(f"Result for None: {_safe_date(None, 'DEFAULT')}")
print(f"Result for '2021-01-01': {_safe_date('2021-01-01', 'DEFAULT')}")

try:
    pd.Timestamp('invalid-date')
except Exception as e:
    print(f"Caught expected error: {e}")
