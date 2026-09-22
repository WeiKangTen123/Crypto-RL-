import os
import shutil
import joblib
from pathlib import Path
import torch
import gc

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CWD_TESTS    = _PROJECT_ROOT / 'train_results' / 'cwd_tests'
_RESULTS_DIR  = _PROJECT_ROOT / 'train_results'

def deep_clean():
    print("--- 1. Cleaning RAM & MPS Cache ---")
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    print("✅ Python/MPS memory released.")

    print("\n--- 2. Clearing Stale Training Files (Disk Cache) ---")
    if _CWD_TESTS.exists():
        shutil.rmtree(_CWD_TESTS)
        os.makedirs(_CWD_TESTS)
        print(f"✅ Cleared {_CWD_TESTS}")

    print("\n--- 3. Marking Stale Trials as FAILED in study.pkl ---")
    folders = [f for f in _RESULTS_DIR.iterdir() if f.is_dir() and f.name.startswith('res_')]
    if not folders:
        print("No result folders found.")
        return

    latest_run = max(folders, key=lambda f: f.stat().st_mtime)
    study_path = latest_run / 'study.pkl'
    
    if study_path.exists():
        try:
            from optuna.trial import TrialState
            study = joblib.load(study_path)
            changed = False
            for t in study.trials:
                if t.state.name == 'RUNNING':
                    study._storage.set_trial_state_values(t._trial_id, state=TrialState.FAIL, values=None)
                    print(f"✅ Marked stale Trial #{t.number} as FAILED in {latest_run.name}")
                    changed = True
            
            if changed:
                joblib.dump(study, study_path)
            else:
                print("No active trials found in study.pkl.")
        except Exception as e:
            print(f"❌ Error updating study.pkl: {e}")

if __name__ == "__main__":
    deep_clean()
