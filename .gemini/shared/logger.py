import os
import fcntl
from datetime import datetime

# Root directory of the project
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def log_to_agent(agent_name, message):
    """
    Appends a message to the specified agent's activity.log in a thread/process-safe manner.
    Format: [YYYY-MM-DD HH:MM] {message}
    """
    log_path = os.path.join(_ROOT, '.gemini', 'skills', agent_name, 'activity.log')
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    formatted_message = f'[{ts}] {message}\n'
    
    try:
        # Open in append mode
        with open(log_path, 'a') as f:
            # Acquire an exclusive lock on the file to prevent race conditions
            # LOCK_EX: Exclusive lock, non-blocking if we fail (just try later)
            # This is a safe way to handle multiple agents writing to their logs.
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(formatted_message)
                f.flush()
            finally:
                # Release the lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        print(f"  [ERROR] Failed to log to {agent_name}: {e}")
