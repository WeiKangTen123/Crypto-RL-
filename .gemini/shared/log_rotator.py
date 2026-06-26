import os
import gzip
import shutil
from datetime import datetime, timedelta

# Root directory
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARCHIVE_DIR = os.path.join(_ROOT, '.gemini', 'logs_archive')

def rotate_log(log_path, days_to_keep=30):
    """
    Compresses and moves logs older than days_to_keep to the archive.
    """
    if not os.path.exists(log_path):
        return

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # Simple rotation: rename active log to timestamped file, then compress
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_path = os.path.join(ARCHIVE_DIR, f"{os.path.basename(log_path)}.{timestamp}")
    
    # Move current log to archive
    shutil.move(log_path, archive_path)
    
    # Compress the moved log
    with open(archive_path, 'rb') as f_in:
        with gzip.open(f"{archive_path}.gz", 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    os.remove(archive_path)
    
    # Cleanup old archives
    cutoff = datetime.now() - timedelta(days=days_to_keep)
    for f in os.listdir(ARCHIVE_DIR):
        f_path = os.path.join(ARCHIVE_DIR, f)
        if os.path.isfile(f_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(f_path))
            if file_time < cutoff:
                os.remove(f_path)
