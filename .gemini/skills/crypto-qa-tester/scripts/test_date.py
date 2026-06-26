import pandas as pd

def _safe_date(d, default):
    try:
        if not d or str(d).lower() == 'invalid-date':
            return default
        pd.Timestamp(d)
        return str(d)
    except Exception:
        return default

print(f"None: {_safe_date(None, '2021-01-01')}")
print(f"Empty: {_safe_date('', '2021-01-01')}")
print(f"invalid-date: {_safe_date('invalid-date', '2021-01-01')}")
print(f"INVALID-DATE: {_safe_date('INVALID-DATE', '2021-01-01')}")
print(f"invalid-date with space: {_safe_date(' invalid-date ', '2021-01-01')}")
print(f"Valid date: {_safe_date('2024-01-01', '2021-01-01')}")
