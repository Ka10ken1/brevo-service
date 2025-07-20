# CSV Processing Configuration

## Directory Setup

The background service can process CSV files in two ways:
1. **Dynamic Path (Recommended)** - Automatically finds CSV files with date-based paths
2. **Static Directory** - Traditional approach using fixed directories

### Dynamic Date-Based CSV Files

For automatically generated CSV files with date-based paths (like your daily exports), configure these environment variables in your `.env` file:

```bash
# Dynamic CSV file configuration
CSV_BASE_PATH=C:\Users\Administrator\Desktop\winners
CSV_FILENAME_PATTERN=applications_{date}_past_1days
CSV_FILE_EXTENSION=.csv
```

**Example for your setup:**
- Path pattern: `C:\Users\Administrator\Desktop\winners\applications_20250718_past_1days.csv`
- The service will automatically replace `{date}` with today's date in YYYYMMDD format
- No need to change the path every day!

### Static Directories (Fallback/Manual Processing)

The service also supports traditional static directories for manual file processing:

- **Input Directory**: `csv_input/` - Place your CSV files here for processing
- **Processed Directory**: `csv_processed/` - Successfully processed files are moved here
- **Failed Directory**: `csv_failed/` - Files with errors are moved here

### Custom Static Directory Configuration (Optional)

You can customize the static directories by setting these environment variables in your `.env` file:

```bash
# Custom CSV directories (optional)
CSV_INPUT_DIR=C:\MyCompany\CSVFiles\Input
CSV_PROCESSED_DIR=C:\MyCompany\CSVFiles\Processed  
CSV_FAILED_DIR=C:\MyCompany\CSVFiles\Failed
```

## Complete .env Configuration Example

```bash
# Brevo API Configuration
BREVO_API_KEY=your_brevo_api_key_here
SENDER_NAME=Your Company Name
SENDER_EMAIL=your@email.com
CAMPAIGN_LIST_ID=1

# Dynamic CSV Configuration (for auto-generated files)
CSV_BASE_PATH=C:\Users\Administrator\Desktop\winners
CSV_FILENAME_PATTERN=applications_{date}_past_1days
CSV_FILE_EXTENSION=.csv

# Static CSV Directories (optional, for manual processing)
CSV_INPUT_DIR=csv_input
CSV_PROCESSED_DIR=csv_processed
CSV_FAILED_DIR=csv_failed
```

## Automatic Processing Schedule

The background service processes CSV files automatically:

- **Every 24 hours at 11:00 AM** - Automatically finds and processes today's CSV file
- **Fallback to yesterday** - If today's file is not found, tries yesterday's file
- **Every 10 minutes** - Checks for files in the `pending_csv` directory
- **Smart path resolution** - Shows available files in logs for troubleshooting

## How Dynamic Path Works

1. **Date Calculation**: Service gets today's date (e.g., 2025-07-18)
2. **Path Generation**: Formats date as YYYYMMDD (20250718)
3. **File Lookup**: Looks for `C:\Users\Administrator\Desktop\winners\applications_20250718_past_1days.csv`
4. **Fallback**: If today's file doesn't exist, tries yesterday's file
5. **Processing**: Processes the file without moving it (leaves it in original location)

## CSV File Format

Your CSV files should have these exact columns (in any order):

```csv
NAT,STOP,ID,Contacts,Email,Website,VendorName,Address,IdCode,Phone,Fax,City,Country
```

### Example CSV Row:
```csv
string,string,406031958,string,contact@example.com,http://website.com,შპს ჯი თი ეარ,address here,string,995599932690,string,Tbilisi,Georgia
```

## Phone Number Validation

- **Georgian mobile numbers**: Must be 9 digits starting with 5 (e.g., `995599932690`)
- **Invalid numbers**: Will be logged as warnings and skipped
- **Supported formats**: 
  - `995599932690` (country code + 9 digits)
  - `599932690` (9 digits starting with 5)
  - `0599932690` (with leading 0)

## File Processing Results

### Dynamic Path Files
- Files are processed in place (not moved)
- Processing results are logged
- Original files remain in their original location

### Static Directory Files
After processing, files are automatically moved:
- ✅ **Successful**: Moved to `csv_processed/` with timestamp
- ❌ **With Errors**: Moved to `csv_failed/` with timestamp
- 🔥 **Critical Errors**: Moved to `csv_failed/` with "ERROR_" prefix

## Manual Processing

### Process Today's File Immediately
```bash
# Restart the service to trigger immediate processing
.\run_service.ps1 restart
```

### Process Specific Date File
The service can process files for specific dates by modifying the date in the path pattern.

## Monitoring and Logs

The service provides detailed logging:

```
2025-01-18 11:00:00 [INFO] Starting daily CSV processing for 2025-01-18
2025-01-18 11:00:00 [INFO] Dynamic CSV Path Configuration:
2025-01-18 11:00:00 [INFO]   - Base Path: C:\Users\Administrator\Desktop\winners
2025-01-18 11:00:00 [INFO]   - Filename Pattern: applications_{date}_past_1days
2025-01-18 11:00:00 [INFO]   - Today's Expected Path: C:\Users\Administrator\Desktop\winners\applications_20250118_past_1days.csv
2025-01-18 11:00:00 [INFO] Found dynamic CSV file: C:\Users\Administrator\Desktop\winners\applications_20250118_past_1days.csv
```

## Troubleshooting

### Dynamic Path Issues

1. **"Expected CSV file not found"**
   - Check if the base path exists: `C:\Users\Administrator\Desktop\winners`
   - Verify the filename pattern matches your actual files
   - The service will list available CSV files in the directory for debugging

2. **Date Format Issues**
   - The service uses YYYYMMDD format (e.g., 20250718 for July 18, 2025)
   - Make sure your CSV files follow this date format

3. **Path Format Issues**
   - Use forward slashes or double backslashes in Windows paths
   - Example: `C:\\Users\\Administrator\\Desktop\\winners` or `C:/Users/Administrator/Desktop/winners`

### Common Issues:

1. **"CSV input directory does not exist"**
   - This is normal when using dynamic paths
   - The service will create static directories automatically for fallback

2. **"No CSV files found"**
   - Check that your dynamic path configuration is correct
   - Ensure files have `.csv` extension
   - Verify the file exists for today's date

3. **"Invalid Georgian phone number format"**
   - Verify phone numbers follow Georgian format (9 digits starting with 5)
   - Check for extra characters or incorrect country codes

4. **"Permission denied"**
   - Ensure the service has read access to the CSV directory
   - Run as administrator if necessary

## Windows Service Setup

The background service runs as a Windows service and will automatically:
1. Create the necessary directories on startup
2. Log all processing activities with dynamic path resolution
3. Handle file permissions and access
4. Process files even when no user is logged in
5. Show expected file paths in logs for easy troubleshooting 