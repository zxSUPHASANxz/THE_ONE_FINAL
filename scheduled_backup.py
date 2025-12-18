"""
Scheduled Auto Backup Script
- Runs daily at specified time
- Validates embeddings count
- Monitors database health
- Sends alerts on errors
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path
import psycopg2

# Setup
BACKUP_DIR = Path(__file__).parent / 'backups'
LOG_DIR = Path(__file__).parent / 'logs'
BACKUP_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f'scheduled_backup_{datetime.now().strftime("%Y%m%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DB_CONFIG = {
    'dbname': 'the_one_db',
    'user': 'suphasan',
    'password': 'Fenrir@4927',
    'host': 'localhost',
    'port': '5433'
}

MIN_EMBEDDINGS = 12000  # Alert if below this
MAX_BACKUP_AGE_HOURS = 24  # Alert if no backup in last 24 hours
KEEP_BACKUPS = 7  # Keep last 7 backups


def check_database_health():
    """Check if database is healthy"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Count embeddings
        cursor.execute("SELECT COUNT(*) FROM document_chunks;")
        count = cursor.fetchone()[0]
        
        # Check for NULL embeddings
        cursor.execute("SELECT COUNT(*) FROM document_chunks WHERE embedding IS NULL;")
        null_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        logger.info(f"📊 Database health check:")
        logger.info(f"   Total embeddings: {count:,}")
        logger.info(f"   NULL embeddings: {null_count}")
        
        # Alerts
        if count < MIN_EMBEDDINGS:
            logger.warning(f"⚠️  Embeddings count below threshold: {count} < {MIN_EMBEDDINGS}")
            return False
        
        if null_count > 0:
            logger.warning(f"⚠️  Found {null_count} NULL embeddings")
        
        logger.info("✓ Database health: OK")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database health check failed: {e}")
        return False


def create_backup():
    """Create database backup"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f'scheduled_backup_{timestamp}.sql'
        
        logger.info(f"📦 Creating backup: {backup_file.name}")
        
        cmd = f'docker exec postgres pg_dump -U suphasan the_one_db > "{backup_file}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            logger.info(f"✓ Backup created: {size_mb:.2f} MB")
            return backup_file
        else:
            logger.error(f"✗ Backup failed: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"✗ Backup error: {e}")
        return None


def cleanup_old_backups():
    """Remove old backups"""
    try:
        # Get all scheduled backups sorted by date
        backups = sorted(
            BACKUP_DIR.glob('scheduled_backup_*.sql'),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if len(backups) > KEEP_BACKUPS:
            for old_backup in backups[KEEP_BACKUPS:]:
                size_mb = old_backup.stat().st_size / (1024 * 1024)
                old_backup.unlink()
                logger.info(f"🗑️  Deleted old backup: {old_backup.name} ({size_mb:.2f} MB)")
        
        logger.info(f"✓ Keeping {min(len(backups), KEEP_BACKUPS)} most recent backups")
        return True
        
    except Exception as e:
        logger.error(f"✗ Cleanup failed: {e}")
        return False


def check_last_backup_age():
    """Check if last backup is recent enough"""
    try:
        backups = list(BACKUP_DIR.glob('*.sql'))
        
        if not backups:
            logger.warning("⚠️  No backups found!")
            return False
        
        latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
        age_hours = (datetime.now().timestamp() - latest_backup.stat().st_mtime) / 3600
        
        logger.info(f"📅 Last backup: {latest_backup.name}")
        logger.info(f"   Age: {age_hours:.1f} hours")
        
        if age_hours > MAX_BACKUP_AGE_HOURS:
            logger.warning(f"⚠️  Last backup is {age_hours:.1f} hours old (max: {MAX_BACKUP_AGE_HOURS})")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Backup age check failed: {e}")
        return False


def verify_backup(backup_file):
    """Verify backup file integrity"""
    try:
        if not backup_file or not backup_file.exists():
            return False
        
        # Check file size
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        
        if size_mb < 1:
            logger.warning(f"⚠️  Backup file suspiciously small: {size_mb:.2f} MB")
            return False
        
        # Check file is readable
        with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline()
            if not first_line:
                logger.error("✗ Backup file is empty")
                return False
        
        logger.info(f"✓ Backup verification passed: {size_mb:.2f} MB")
        return True
        
    except Exception as e:
        logger.error(f"✗ Backup verification failed: {e}")
        return False


def generate_status_report():
    """Generate backup status report"""
    try:
        backups = sorted(BACKUP_DIR.glob('*.sql'), key=lambda x: x.stat().st_mtime, reverse=True)
        
        total_size = sum(b.stat().st_size for b in backups) / (1024 * 1024)
        
        report = f"""
{'='*70}
📊 BACKUP STATUS REPORT
{'='*70}

📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📦 Backups:
   Total: {len(backups)}
   Total size: {total_size:.2f} MB
   Keeping: {KEEP_BACKUPS} most recent

Recent backups:
"""
        for i, backup in enumerate(backups[:5], 1):
            size = backup.stat().st_size / (1024 * 1024)
            age_hours = (datetime.now().timestamp() - backup.stat().st_mtime) / 3600
            report += f"   {i}. {backup.name}\n"
            report += f"      Size: {size:.2f} MB, Age: {age_hours:.1f}h\n"
        
        report += f"\n{'='*70}\n"
        
        logger.info(report)
        
        # Save report
        report_file = LOG_DIR / f'backup_status_{datetime.now().strftime("%Y%m%d")}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Report generation failed: {e}")
        return False


def main():
    """Main execution"""
    logger.info("🚀 Starting Scheduled Backup Process")
    
    success = True
    
    # Step 1: Check database health
    if not check_database_health():
        logger.warning("⚠️  Database health check failed")
        success = False
    
    # Step 2: Check last backup age
    check_last_backup_age()
    
    # Step 3: Create new backup
    backup_file = create_backup()
    if not backup_file:
        logger.error("❌ Backup creation failed")
        success = False
    
    # Step 4: Verify backup
    if backup_file and not verify_backup(backup_file):
        logger.error("❌ Backup verification failed")
        success = False
    
    # Step 5: Cleanup old backups
    cleanup_old_backups()
    
    # Step 6: Generate report
    generate_status_report()
    
    if success:
        logger.info("✅ Scheduled backup completed successfully")
    else:
        logger.error("❌ Scheduled backup completed with errors")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
