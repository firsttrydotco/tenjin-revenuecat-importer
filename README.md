# Tenjin RevenueCat Importer

Python tool to import attribution data from RevenueCat to Tenjin Import Attribution API.

## 📋 Overview

This project allows you to:
1. Extract attribution identifiers from RevenueCat Customers exports
2. Format data for Tenjin API
3. Send attributions to Tenjin in an optimized way (parallel async requests)

### 🔑 Supported Identifiers

**iOS:**
- **IDFA** (advertising_id): Apple advertising identifier
- **IDFV** (developer_device_id): Apple developer identifier

**Android:**
- **GAID** (advertising_id): Google Advertising ID
- **Android ID** (developer_device_id): Android developer identifier

⚠️ **Important**: The tool sends **both identifiers simultaneously** (advertising_id + developer_device_id) to Tenjin for each user. This ensures better attribution even if one identifier is missing or changes.

## 🚀 Installation

```bash
pip install -r requirements.txt
```

## 📖 Usage

### 1. Extract data from RevenueCat

From a RevenueCat **Customers** export:
```bash
python3 extract_idfa_idfv_customers.py input_customers.csv output.csv
```

The script extracts `idfa` and `idfv` columns (or Android equivalents) and creates a file with unique combinations.

### 2. Format for Tenjin

```bash
python3 format_for_tenjin.py input.csv tenjin_formatted.csv
```

Options:
- `--keep-zero-idfa`: Keep zero IDFAs (default: ignored)

### 3. Import to Tenjin

#### Quick test (100 lines)
```bash
export TENJIN_SDK_KEY=your_sdk_key_here
export BUNDLE_ID=your.bundle.id
python3 send_to_tenjin_fast.py --max-lines 100 --bundle-id $BUNDLE_ID
```

✅ Verify success rate = 100%

#### Full import

**Option 1: Foreground (see logs)**
```bash
export TENJIN_SDK_KEY=your_sdk_key_here
export BUNDLE_ID=your.bundle.id
python3 send_to_tenjin_fast.py --log-file tenjin_import.log --bundle-id $BUNDLE_ID
```

**Stop with:** `Ctrl+C`

**Option 2: Background (recommended)**
```bash
export TENJIN_SDK_KEY=your_sdk_key_here
export BUNDLE_ID=your.bundle.id
nohup python3 send_to_tenjin_fast.py --log-file tenjin_import.log --bundle-id $BUNDLE_ID > console.log 2>&1 &
echo $! > tenjin.pid
```

**Monitor progress:**
```bash
tail -f tenjin_import.log
```

**Stop the process:**
```bash
kill $(cat tenjin.pid)
```

#### Advanced options
```bash
# Resume after interruption
python3 send_to_tenjin_fast.py --start-line 50001 --log-file import.log --bundle-id your.bundle.id

# Adjust speed
python3 send_to_tenjin_fast.py --delay 0.01 --concurrency 50 --bundle-id your.bundle.id

# Dry-run mode (simulation)
python3 send_to_tenjin_fast.py --dry-run --max-lines 10 --bundle-id your.bundle.id
```

## ⚙️ Configuration

Default parameters can be modified via command line arguments:

- `--sdk-key`: Tenjin SDK Key (default: from TENJIN_SDK_KEY env var, **required**)
- `--bundle-id`: Application bundle ID (**required**)
- `--platform`: Platform (`ios` or `android`, default: `ios`)
- `--delay`: Delay between requests in seconds (default: 0.01)
- `--concurrency`: Number of concurrent requests (default: 50)
- `--batch-size`: Batch size for progress reports (default: 1000)

## 📊 Performance

| Configuration | Speed | Time for 500K lines |
|---------------|-------|---------------------|
| `--delay 0` | ~100 req/s | ~1h30 |
| `--delay 0.01` (default) | ~70 req/s | ~2h |
| `--delay 0.05` | ~30 req/s | ~4h |
| `--delay 0.1` | ~15 req/s | ~8h |

## 📁 Project Structure

```
.
├── extract_idfa_idfv_customers.py    # Extract from RevenueCat customers
├── format_for_tenjin.py              # Format for Tenjin API
├── send_to_tenjin.py                 # Synchronous import (slow)
├── send_to_tenjin_fast.py            # Fast async import (recommended)
├── README.md                         # This file
├── requirements.txt                  # Python dependencies
└── sample_data.csv                   # Sample data file
```

## 📤 Data Format Sent

Each request to Tenjin contains **both identifiers simultaneously**:

- **`advertising_id`**: IDFA (iOS) or GAID (Android) - can be empty
- **`developer_device_id`**: IDFV (iOS) or Android ID (Android) - required

This approach ensures better attribution even if one identifier is missing or changes over time.

## 🔐 Security

⚠️ **Important**:
- Never commit CSV files containing real data
- Use environment variables for sensitive SDK keys
- Logs may contain user identifiers

**SDK Key Configuration:**
```bash
# Set environment variable (recommended)
export TENJIN_SDK_KEY=your_sdk_key_here

# Or pass via command line
python3 send_to_tenjin_fast.py --sdk-key your_sdk_key_here --bundle-id your.bundle.id
```

## 📝 Log Format

### Progress logs (every 1000 sends)

```
2025-12-02 17:15:30 - INFO - 📊 Line 50,000 | Sent: 50,000 | Success: 49,987 (99.97%) | Errors: 13 | Speed: 98.5 req/s | ETA: 1h 15m
```

**Details:**
- **Line X**: Current CSV line
- **Sent**: Total number of requests sent
- **Success**: Number of successful requests (HTTP 200/201/204)
- **Errors**: Number of errors
- **Speed**: Requests per second (over last 1000)
- **ETA**: Estimated time remaining

### Error logs

```
2025-12-02 17:15:35 - ERROR - ✗ Line 50,123: HTTP 429 - Rate limit exceeded
```

## 🐛 Troubleshooting

### Error 429 (Rate Limiting)

**Symptom**: `HTTP 429 - Too Many Requests`

**Solution:**
```bash
# Slow down requests
python3 send_to_tenjin_fast.py --delay 0.1 --batch-size 500 --bundle-id your.bundle.id
```

### Error 401 (Unauthorized)

**Symptom**: `HTTP 401 - Unauthorized`

**Checks:**
1. SDK key is correct (check TENJIN_SDK_KEY environment variable)
2. Key has not expired
3. Contact Tenjin support if problem persists

### Error 400 (Bad Request)

**Symptom**: `HTTP 400 - Bad Request`

**Possible causes:**
- Incorrect IDFA/IDFV/GAID/Android ID format (must be lowercase without dashes)
- Incorrect bundle ID
- Check the problematic line in logs

**Required format:**
- Identifiers must be **lowercase** and **without dashes**
- Example: `f024e65f3dd94f16983726bcef192d68` (not `F024E65F-3DD9-4F16-9837-26BCEF192D68`)

### Lost Connection

Script stops if:
- Internet connection lost
- Timeout after 10 seconds

**Solution**: Resume where it stopped:
```bash
# Find last processed line
grep "📊 Line" import.log | tail -1

# Resume
python3 send_to_tenjin_fast.py --start-line <line> --log-file import.log --bundle-id your.bundle.id
```

### Too Many Consecutive Errors

Script automatically stops if **10 consecutive errors** occur at the beginning (likely configuration issue).

**Check:**
1. Error logs
2. Configuration (SDK key, bundle ID)
3. Connectivity

## 📈 Progress Monitoring

### During execution

```bash
# Real-time logs
tail -f tenjin_import.log

# Count processed lines
grep "📊 Line" tenjin_import.log | wc -l

# Last progress
grep "📊 Line" tenjin_import.log | tail -1

# Total number of errors
grep "ERROR" tenjin_import.log | wc -l
```

### After execution

Script automatically displays a summary:

```
======================================================================
📊 IMPORT SUMMARY
======================================================================
Total duration: 1h 45m 32s
Total sent: 515,702
✓ Success: 515,450 (99.95%)
✗ Errors: 252
Success rate: 99.95%
Average speed: 81.23 req/s
======================================================================
```

## 🎯 Recommended Workflow

### Step 1: Initial Test
```bash
export TENJIN_SDK_KEY=your_sdk_key_here
export BUNDLE_ID=your.bundle.id
python3 send_to_tenjin_fast.py --max-lines 100 --bundle-id $BUNDLE_ID
```
✅ Verify: 100% success

### Step 2: Tenjin Dashboard Verification
- Go to Tenjin dashboard
- Verify users appear
- Confirm data is correct

### Step 3: Full Launch
```bash
# Background with logs
export TENJIN_SDK_KEY=your_sdk_key_here
export BUNDLE_ID=your.bundle.id
nohup python3 send_to_tenjin_fast.py --log-file tenjin_import.log --bundle-id $BUNDLE_ID > console.log 2>&1 &

# Note the process PID
echo $! > tenjin_import.pid
```

### Step 4: Monitoring
```bash
# Follow logs
tail -f tenjin_import.log

# Check process
cat tenjin_import.pid | xargs ps -p
```

### Step 5: Final Verification
Once complete, verify in Tenjin dashboard:
- Number of imported users
- Installation dates (= import date)
- Organic vs paid distribution

## 📞 Support

### If you have problems

1. **Check logs**: `tenjin_import.log`
2. **Search for errors**: `grep ERROR tenjin_import.log`
3. **Test with sample**: `--max-lines 10`
4. **Contact Tenjin Support**: support@tenjin.com

### Useful information for support

- Platform: `ios` or `android`
- API endpoint: `https://track.tenjin.io/v0/import_attribution`
- Identifier format: lowercase, without dashes
- **Identifiers sent**: `advertising_id` (IDFA/GAID) + `developer_device_id` (IDFV/Android ID) simultaneously

## ✅ Checklist Before Full Import

- [ ] Test with 100 lines successful (100% success)
- [ ] Verification in Tenjin dashboard
- [ ] File `tenjin_formatted_all.csv` present
- [ ] Stable internet connection
- [ ] Enough disk space for logs (~50MB)
- [ ] Time available (~2h minimum)
- [ ] `TENJIN_SDK_KEY` environment variable set
- [ ] `--bundle-id` argument provided

**🚀 Ready? Launch the import!**
