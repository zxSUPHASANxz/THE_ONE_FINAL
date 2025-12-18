"""
Auto Scrape and Embed with Safety Features
- Auto backup before scraping
- Error detection and recovery
- Logging system
- Retry mechanism
- Data validation
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

# Setup logging
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

log_filename = LOG_DIR / f'scrape_embed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'dbname': 'the_one_db',
    'user': 'suphasan',
    'password': 'Fenrir@4927',
    'host': 'localhost',
    'port': '5433'
}

# Backup configuration
BACKUP_DIR = Path(__file__).parent / 'backups'
BACKUP_DIR.mkdir(exist_ok=True)


class SafeScrapeEmbedder:
    def __init__(self):
        self.conn = None
        self.backup_file = None
        self.start_time = datetime.now()
        self.stats = {
            'initial_count': 0,
            'scraped_count': 0,
            'embedded_count': 0,
            'errors': 0,
            'backup_size': 0
        }
    
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("✓ Database connection established")
            return True
        except Exception as e:
            logger.error(f"✗ Database connection failed: {e}")
            return False
    
    def backup_database(self):
        """Create automatic backup before operations"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_file = BACKUP_DIR / f'auto_backup_{timestamp}.sql'
            
            logger.info(f"📦 Creating backup: {self.backup_file.name}")
            
            # Use Docker to backup
            cmd = f'docker exec postgres pg_dump -U suphasan the_one_db > "{self.backup_file}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                backup_size = self.backup_file.stat().st_size / (1024 * 1024)  # MB
                self.stats['backup_size'] = backup_size
                logger.info(f"✓ Backup created: {backup_size:.2f} MB")
                return True
            else:
                logger.error(f"✗ Backup failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"✗ Backup error: {e}")
            return False
    
    def get_current_stats(self):
        """Get current database statistics"""
        try:
            cursor = self.conn.cursor()
            
            # Count documents
            cursor.execute("SELECT COUNT(*) FROM documents;")
            doc_count = cursor.fetchone()[0]
            
            # Count embeddings
            cursor.execute("SELECT COUNT(*) FROM document_chunks;")
            chunk_count = cursor.fetchone()[0]
            
            # Count sources
            cursor.execute("SELECT COUNT(*) FROM sources;")
            source_count = cursor.fetchone()[0]
            
            cursor.close()
            
            self.stats['initial_count'] = chunk_count
            
            logger.info(f"📊 Current stats:")
            logger.info(f"   Sources: {source_count}")
            logger.info(f"   Documents: {doc_count}")
            logger.info(f"   Embeddings: {chunk_count:,}")
            
            return True
        except Exception as e:
            logger.error(f"✗ Stats query failed: {e}")
            return False
    
    def validate_data_integrity(self):
        """Validate data integrity before and after operations"""
        try:
            cursor = self.conn.cursor()
            
            # Check for NULL embeddings
            cursor.execute("SELECT COUNT(*) FROM document_chunks WHERE embedding IS NULL;")
            null_count = cursor.fetchone()[0]
            
            if null_count > 0:
                logger.warning(f"⚠️  Found {null_count} chunks without embeddings")
            
            # Check for orphaned chunks
            cursor.execute("""
                SELECT COUNT(*) FROM document_chunks dc
                LEFT JOIN documents d ON dc.document_id = d.id
                WHERE d.id IS NULL;
            """)
            orphan_count = cursor.fetchone()[0]
            
            if orphan_count > 0:
                logger.warning(f"⚠️  Found {orphan_count} orphaned chunks")
            
            cursor.close()
            
            if null_count == 0 and orphan_count == 0:
                logger.info("✓ Data integrity verified")
                return True
            return False
        except Exception as e:
            logger.error(f"✗ Integrity check failed: {e}")
            return False
    
    def scrape_with_retry(self, max_retries=3):
        """Scrape data with retry mechanism"""
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🔍 Scraping attempt {attempt}/{max_retries}")
                
                # Import and run your scraper
                # Replace with your actual scraper import
                # from scraper.pantip_scraper import scrape_pantip
                # results = scrape_pantip()
                
                # For now, simulate success
                logger.info("✓ Scraping completed (simulated)")
                self.stats['scraped_count'] = 10  # Simulated
                return True
                
            except Exception as e:
                logger.error(f"✗ Scraping attempt {attempt} failed: {e}")
                self.stats['errors'] += 1
                
                if attempt == max_retries:
                    logger.error("✗ Max retries reached for scraping")
                    return False
                
                # Wait before retry (exponential backoff)
                import time
                wait_time = 2 ** attempt
                logger.info(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        return False
    
    def embed_with_checkpoint(self):
        """Embed data with checkpoint saving"""
        try:
            logger.info("🔄 Starting embedding process...")
            
            # Import your embedding function
            # from embedding.embed_with_huggingface import embed_documents
            # embed_documents()
            
            # For now, simulate success
            logger.info("✓ Embedding completed (simulated)")
            self.stats['embedded_count'] = 10  # Simulated
            return True
            
        except Exception as e:
            logger.error(f"✗ Embedding failed: {e}")
            self.stats['errors'] += 1
            return False
    
    def rollback_if_failed(self):
        """Rollback to backup if operations failed"""
        try:
            if not self.backup_file or not self.backup_file.exists():
                logger.error("✗ No backup file to rollback to")
                return False
            
            logger.warning("🔄 Rolling back to backup...")
            
            cmd = f'docker exec -i postgres psql -U suphasan -d the_one_db < "{self.backup_file}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✓ Rollback successful")
                return True
            else:
                logger.error(f"✗ Rollback failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"✗ Rollback error: {e}")
            return False
    
    def generate_report(self):
        """Generate operation report"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        report = f"""
{'='*70}
📊 SCRAPE & EMBED REPORT
{'='*70}

⏱️  Duration: {duration:.2f}s
📦 Backup: {self.backup_file.name if self.backup_file else 'None'}
   Size: {self.stats['backup_size']:.2f} MB

📈 Statistics:
   Initial embeddings: {self.stats['initial_count']:,}
   Scraped items: {self.stats['scraped_count']:,}
   New embeddings: {self.stats['embedded_count']:,}
   Errors: {self.stats['errors']}

📁 Log file: {log_filename.name}

{'='*70}
"""
        logger.info(report)
        
        # Save report to file
        report_file = LOG_DIR / f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return report
    
    def cleanup_old_backups(self, keep_last=5):
        """Clean up old backup files, keep only last N"""
        try:
            backups = sorted(BACKUP_DIR.glob('auto_backup_*.sql'), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if len(backups) > keep_last:
                for old_backup in backups[keep_last:]:
                    old_backup.unlink()
                    logger.info(f"🗑️  Deleted old backup: {old_backup.name}")
            
            return True
        except Exception as e:
            logger.error(f"✗ Cleanup failed: {e}")
            return False
    
    def run(self):
        """Main execution flow with safety checks"""
        logger.info("🚀 Starting Safe Scrape & Embed Process")
        logger.info(f"   Timestamp: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Connect to database
        if not self.connect_db():
            logger.error("❌ Cannot proceed without database connection")
            return False
        
        # Step 2: Get initial statistics
        if not self.get_current_stats():
            logger.error("❌ Cannot proceed without database stats")
            return False
        
        # Step 3: Create backup
        if not self.backup_database():
            logger.error("❌ Cannot proceed without backup")
            return False
        
        # Step 4: Validate data integrity
        self.validate_data_integrity()
        
        # Step 5: Scrape with retry
        scrape_success = self.scrape_with_retry()
        
        # Step 6: Embed with checkpoint
        embed_success = False
        if scrape_success:
            embed_success = self.embed_with_checkpoint()
        
        # Step 7: Validate after operations
        if scrape_success and embed_success:
            logger.info("✓ All operations successful")
            self.validate_data_integrity()
        else:
            logger.error("❌ Operations failed")
            
            # Ask user before rollback
            print("\n⚠️  Operations failed. Rollback to backup? (y/n): ", end='')
            response = input().lower()
            if response == 'y':
                self.rollback_if_failed()
        
        # Step 8: Cleanup old backups
        self.cleanup_old_backups()
        
        # Step 9: Generate report
        self.generate_report()
        
        # Close connection
        if self.conn:
            self.conn.close()
            logger.info("✓ Database connection closed")
        
        logger.info("🏁 Process completed")
        return scrape_success and embed_success


def main():
    """Entry point"""
    scraper = SafeScrapeEmbedder()
    success = scraper.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
