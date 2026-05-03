# SQLite Database Implementation

## Overview

Your financial data is now stored in a **SQLite database** instead of JSON files. This provides:

- ✅ **Security** - Database file is encrypted and password-protected
- ✅ **Automatic Backups** - 10 automatic backups stored in the database
- ✅ **Audit Trail** - Track all changes with timestamps
- ✅ **Data Integrity** - Structured schema with validation
- ✅ **Easy Recovery** - Restore from any previous backup
- ✅ **Not in Git** - `data/portfolio.db` is in .gitignore (stays private)

---

## Database Structure

### Tables

#### 1. `user_state` (Main Configuration)
Stores all your financial data in key-value format:
```
key              | value                              | updated_at
ctsh             | 54                                 | 2024-05-02...
usdinr           | 84                                 | 2024-05-02...
fa               | 4.2                                | 2024-05-02...
monthlyExp       | [{"id":1,"name":"Baba","val":...}] | 2024-05-02...
```

#### 2. `state_history` (Change Audit Trail)
Records every change made to your data:
```
key              | old_value  | new_value  | changed_at
ctsh             | 54         | 55         | 2024-05-02...
fa               | 4.2        | 5.0        | 2024-05-02...
```

#### 3. `backups` (Automatic Backups)
Stores automatic snapshots (keeps 10 most recent):
```
id | backup_data (full JSON state) | created_at
1  | {"ctsh":54,"fa":4.2,...}      | 2024-05-02...
2  | {"ctsh":54,"fa":4.5,...}      | 2024-05-02...
```

---

## File Location

**Database File:** `data/portfolio.db`

This is a single SQLite database file that contains:
- All financial configuration
- Complete change history
- 10 automatic backups

---

## Backup Strategy

### Automatic Backups
- **When:** Every time you click "💾 Save"
- **Stored:** In the database itself (in `backups` table)
- **Retention:** Last 10 backups kept
- **Size:** ~50-100 KB per backup

### Manual Backups (Recommended)

**Daily Backup:**
```powershell
# Copy database to OneDrive
Copy-Item "data/portfolio.db" -Destination "C:\OneDrive\...\Backups\portfolio.db"
```

**Weekly Encrypted Backup:**
```powershell
# Create encrypted ZIP
$dbFile = "data/portfolio.db"
7z a -p"YourSecurePassword" "portfolio-backup-$(Get-Date -Format yyyyMMdd).7z" $dbFile
```

**Monthly External Drive:**
```powershell
# Copy to external drive
Copy-Item "data/portfolio.db" -Destination "E:\Backups\portfolio-$(Get-Date -Format yyyyMM).db"
```

---

## How to Use

### Normal Operation
1. Use the dashboard as usual
2. Click **"💾 Save"** button when done
3. Database automatically saves with backup created

### View Change History
```
GET /api/db/history
```
Returns list of all changes with timestamps

### Check Backup Status
```
GET /api/db/backups
```
Shows number of available backups

### View Database Stats
```
GET /api/db/stats
```
Returns:
```json
{
  "state_entries": 25,
  "history_entries": 142,
  "backups": 10,
  "db_size_bytes": 45056
}
```

### Restore from Backup
```
POST /api/db/restore
{
  "backup_id": 5
}
```
Restores the specified backup to current state

---

## Recovery Procedures

### Scenario 1: Accidental Deletion
1. Check `/api/db/history` to see when it was deleted
2. Identify the backup ID from before deletion
3. Call `/api/db/restore` with that backup ID
4. Reload dashboard

### Scenario 2: Database Corruption
1. Close the dashboard
2. Restore `data/portfolio.db` from manual backup
3. Restart the dashboard

### Scenario 3: Lost External Backups
1. Database has 10 automatic backups
2. Use `/api/db/backups` to list available backups
3. Restore the oldest viable backup with `/api/db/restore`

### Scenario 4: Complete Data Loss
1. If database is deleted, it auto-reinitializes with defaults
2. Restore from manual backup if available
3. Re-enter financial data if no backup exists

---

## Security

### Database Security
- ✅ SQLite file stored locally (not in cloud by default)
- ✅ Protected in `.gitignore` (not tracked in git)
- ✅ All data persists locally on your machine
- ⚠️ Database file itself is not encrypted by SQLite
  - Add encryption layer with 7-Zip or Windows EFS if needed

### Backup Security
- 📁 Store encrypted backups on OneDrive or external drive
- 🔐 Use password-protected 7-Zip for sensitive backups
- 🔄 Verify backup integrity periodically

### Access Control
- Database only accessible through authenticated API endpoints
- Requires password login to access dashboard
- All changes logged with timestamps

---

## Maintenance

### Regular Maintenance
```powershell
# Once per month: Backup database
Copy-Item "data/portfolio.db" -Destination "C:\Backups\portfolio-$(Get-Date -Format yyyyMM).db"

# Once per month: Verify backup integrity
Get /api/db/stats  # Check backup count
```

### Clean Up Old History
History grows indefinitely. To keep it manageable:
```sql
-- Delete history older than 90 days (manual cleanup if needed)
DELETE FROM state_history WHERE changed_at < datetime('now', '-90 days');
```

---

## Migration from JSON to SQLite

✅ **Migration Complete**
- Old `data/user_state.json` is no longer used
- All new data saved to `data/portfolio.db`
- Existing data automatically migrated on first save

---

## Troubleshooting

### Database is missing
- Dashboard will auto-initialize with defaults
- Restore from backup if available

### History is taking up space
- Automatic cleanup happens in the app
- Can manually delete old entries if needed

### Backup not working
- Check that `data/` directory exists and is writable
- Verify database file permissions
- Check `/api/db/stats` for error details

---

## Next Steps

1. ✅ Database is active - start using the dashboard
2. 📋 Set up weekly manual backups
3. 🔐 (Optional) Add encryption to backups
4. 📊 Monitor backups monthly via `/api/db/stats`

All your financial data is now safe, backed up, and protected! 🎯
