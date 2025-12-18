# Auto Scrape & Embed System - README

## 📋 ภาพรวม

ระบบสำรองข้อมูลและป้องกัน error อัตโนมัติสำหรับการ scrape และ embed ข้อมูล

## 🛡️ Features

### 1. Auto Backup System
- ✅ สำรองข้อมูลก่อนทุกการ scrape/embed
- ✅ เก็บ backup หลายเวอร์ชัน (configurable)
- ✅ Auto cleanup backups เก่า
- ✅ Verify backup integrity

### 2. Error Protection
- ✅ Retry mechanism (exponential backoff)
- ✅ Error logging ทุก step
- ✅ Auto rollback เมื่อเกิด error
- ✅ Data validation ก่อนและหลังทำงาน

### 3. Monitoring & Logging
- ✅ Detailed logs ทุก operation
- ✅ Database health checks
- ✅ Embedding count validation
- ✅ Status reports

### 4. Scheduled Backups
- ✅ Daily auto backup (configurable time)
- ✅ Windows Task Scheduler integration
- ✅ Alert เมื่อ backup ล้มเหลว

## 📁 Files

```
THE__ONE_V3/
├── auto_scrape_with_safety.py    # Main scrape & embed with safety
├── scheduled_backup.py             # Scheduled backup script
├── setup_scheduled_backup.ps1     # Setup Windows Task Scheduler
├── backups/                        # Auto backups directory
│   ├── auto_backup_YYYYMMDD_HHMMSS.sql
│   └── scheduled_backup_YYYYMMDD_HHMMSS.sql
└── logs/                           # Logs directory
    ├── scrape_embed_YYYYMMDD_HHMMSS.log
    ├── scheduled_backup_YYYYMMDD.log
    └── report_YYYYMMDD_HHMMSS.txt
```

## 🚀 การใช้งาน

### 1. Run Manual Scrape & Embed (with safety)

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run safe scrape & embed
python auto_scrape_with_safety.py
```

**Process:**
1. ✅ Connect to database
2. ✅ Get current statistics
3. ✅ **Create backup** (150+ MB)
4. ✅ Validate data integrity
5. ✅ Scrape with retry (max 3 attempts)
6. ✅ Embed with checkpoint
7. ✅ Validate after operations
8. ⚠️ **Auto rollback if failed**
9. ✅ Cleanup old backups
10. ✅ Generate report

### 2. Setup Scheduled Daily Backup

```powershell
# Run setup script (requires admin)
.\setup_scheduled_backup.ps1
```

**Configuration:**
- Default time: **2:00 AM daily**
- Keeps last **7 backups**
- Alerts if embeddings < 12,000
- Validates backup integrity

### 3. Manual Backup

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run scheduled backup script
python scheduled_backup.py
```

## ⚙️ Configuration

### Auto Scrape Safety (`auto_scrape_with_safety.py`)

```python
# Retry configuration
max_retries = 3  # Max scraping attempts

# Backup retention
keep_last = 5  # Keep last 5 backups
```

### Scheduled Backup (`scheduled_backup.py`)

```python
MIN_EMBEDDINGS = 12000          # Alert threshold
MAX_BACKUP_AGE_HOURS = 24       # Alert if no backup in 24h
KEEP_BACKUPS = 7                # Keep last 7 backups
```

### Task Scheduler (`setup_scheduled_backup.ps1`)

```powershell
$taskTime = "02:00"  # Daily backup time
```

## 📊 Output Examples

### Success Report

```
======================================================================
📊 SCRAPE & EMBED REPORT
======================================================================

⏱️  Duration: 45.23s
📦 Backup: auto_backup_20251218_163000.sql
   Size: 150.76 MB

📈 Statistics:
   Initial embeddings: 12,208
   Scraped items: 150
   New embeddings: 150
   Errors: 0

📁 Log file: scrape_embed_20251218_163000.log

======================================================================
```

### Backup Status Report

```
======================================================================
📊 BACKUP STATUS REPORT
======================================================================

📅 Date: 2025-12-18 16:30:00

📦 Backups:
   Total: 7
   Total size: 1,055.32 MB
   Keeping: 7 most recent

Recent backups:
   1. scheduled_backup_20251218_020000.sql
      Size: 150.76 MB, Age: 14.5h
   2. scheduled_backup_20251217_020000.sql
      Size: 150.72 MB, Age: 38.5h

======================================================================
```

## 🔧 Troubleshooting

### Problem: Backup failed

**Solution:**
```powershell
# Check if Docker is running
docker ps

# Check database connection
docker exec postgres psql -U suphasan -d the_one_db -c "SELECT COUNT(*) FROM document_chunks;"
```

### Problem: Cannot rollback

**Solution:**
```powershell
# Manual restore from backup
docker exec -i postgres psql -U suphasan -d the_one_db < backups/auto_backup_YYYYMMDD_HHMMSS.sql
```

### Problem: Task Scheduler not working

**Solution:**
```powershell
# Check task status
Get-ScheduledTask -TaskName "THE_ONE_AutoBackup"

# View task history
Get-ScheduledTask -TaskName "THE_ONE_AutoBackup" | Get-ScheduledTaskInfo

# Run manually
Start-ScheduledTask -TaskName "THE_ONE_AutoBackup"
```

## 📝 Logs Location

All logs saved to: `D:\Project\THE__ONE_V3\logs\`

- **Scrape logs:** `scrape_embed_YYYYMMDD_HHMMSS.log`
- **Backup logs:** `scheduled_backup_YYYYMMDD.log`
- **Reports:** `report_YYYYMMDD_HHMMSS.txt`

## ⚠️ Important Notes

1. **Disk Space:** Backups are ~150 MB each. Keep enough disk space.
2. **Rollback:** Always test backup restoration before major operations.
3. **Logs:** Check logs regularly for warnings/errors.
4. **Testing:** Test the system before relying on it in production.

## 🎯 Best Practices

### Before Scraping:
1. ✅ Check database health
2. ✅ Ensure enough disk space
3. ✅ Verify last backup exists
4. ✅ Run with safety script

### After Scraping:
1. ✅ Check logs for errors
2. ✅ Validate embedding count
3. ✅ Verify data integrity
4. ✅ Review reports

### Regular Maintenance:
1. ✅ Check scheduled backup runs
2. ✅ Review disk space usage
3. ✅ Clean old logs (manually if needed)
4. ✅ Test restore process monthly

## 📞 Emergency Recovery

If everything fails:

```powershell
# 1. Stop all scraping
# 2. Find latest good backup
Get-ChildItem backups/*.sql | Sort-Object LastWriteTime -Descending | Select-Object -First 5

# 3. Restore manually
docker exec -i postgres psql -U suphasan -d the_one_db < backups/[BACKUP_FILE].sql

# 4. Verify
docker exec postgres psql -U suphasan -d the_one_db -c "SELECT COUNT(*) FROM document_chunks;"
```

## 🔐 Security

- Database credentials stored in script (consider using environment variables for production)
- Backups contain sensitive data - secure backup directory
- Log files may contain database connection info - protect log directory

## 📈 Future Enhancements

- [ ] Email alerts on backup failures
- [ ] Remote backup to cloud storage
- [ ] Incremental backups
- [ ] Compression of old backups
- [ ] Web dashboard for monitoring
- [ ] Slack/Discord notifications
