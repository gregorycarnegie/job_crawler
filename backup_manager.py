# =============================================================================
# Backup System
# =============================================================================

import logging
import os
import shutil
import sqlite3
import time
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from monitoring_config import MonitoringConfig


class BackupManager:
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger("job_agent.backup")
    
    def backup_database(self) -> bool:
        """Create database backup - FIXED VERSION."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"jobs_backup_{timestamp}.db"

            # Copy database file
            db_path = os.getenv("DATABASE_PATH", "data/jobs.db")

            # CRITICAL FIX: Proper file existence check
            if not Path(db_path).exists():
                self.logger.warning(f"Database file not found: {db_path}")
                return False

            # Use SQLite backup for better Windows compatibility
            try:
                source_conn = sqlite3.connect(db_path)
                backup_conn = sqlite3.connect(str(backup_file))

                source_conn.backup(backup_conn)

                source_conn.close()
                backup_conn.close()

                # Small delay for Windows file system
                time.sleep(0.1)
                
            except Exception as backup_error:
                self.logger.warning(f"SQLite backup failed: {backup_error}, trying file copy")
                # Fallback to file copy
                try:
                    shutil.copy2(db_path, backup_file)
                except Exception as copy_error:
                    self.logger.error(f"File copy also failed: {copy_error}")
                    return False

            # Compress backup
            try:
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Remove uncompressed backup with retry for Windows
                for attempt in range(3):
                    try:
                        backup_file.unlink()
                        break
                    except (PermissionError, FileNotFoundError):
                        if attempt < 2:
                            time.sleep(0.5)
                        # Ignore final failure - compressed backup exists

                self.logger.info(f"Database backup created: {backup_file}.gz")
                return True
                
            except Exception as compress_error:
                self.logger.error(f"Backup compression failed: {compress_error}")
                return False

        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            return False
    
    def cleanup_old_backups(self):
        """Remove old backup files."""
        try:
            cutoff_date = datetime.now() - timedelta(days=MonitoringConfig.BACKUP_RETENTION_DAYS)
            
            for backup_file in self.backup_dir.glob("*.gz"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    self.logger.info(f"Removed old backup: {backup_file}")
                    
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")
