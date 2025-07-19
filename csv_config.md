# CSV Processing Configuration

## Directory Setup

The background service automatically processes CSV files from specific directories. You can customize these locations using environment variables.

### Default Directories (created automatically)

- **Input Directory**: `csv_input/` - Place your CSV files here for processing
- **Processed Directory**: `csv_processed/` - Successfully processed files are moved here
- **Failed Directory**: `csv_failed/` - Files with errors are moved here

### Custom Directory Configuration (Optional)

You can customize the directories by setting these environment variables in your `.env` file:

```bash
# Custom CSV directories (optional)
CSV_INPUT_DIR=C:\MyCompany\CSVFiles\Input
CSV_PROCESSED_DIR=C:\MyCompany\CSVFiles\Processed  
CSV_FAILED_DIR=C:\MyCompany\CSVFiles\Failed
```

## Automatic Processing Schedule

The background service processes CSV files automatically:

- **Every 24 hours at 11:00 AM** - Processes all CSV files in the input directory
- **Every 10 minutes** - Checks for files in the `pending_csv` directory

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

After processing, files are automatically moved:

- ✅ **Successful**: Moved to `csv_processed/` with timestamp
- ❌ **With Errors**: Moved to `csv_failed/` with timestamp
- 🔥 **Critical Errors**: Moved to `csv_failed/` with "ERROR_" prefix

## Manual Processing

To manually trigger CSV processing (without waiting for the schedule):

1. **Place CSV files** in the `csv_input/` directory
2. **Restart the service** or wait for the next scheduled run
3. **Check logs** for processing results

## Monitoring

Check the service logs for:
- Processing start/completion times
- Number of contacts processed
- Any validation errors
- File movement confirmations

## Windows Service Setup

The background service runs as a Windows service and will automatically:
1. Create the necessary directories on startup
2. Log all processing activities  
3. Handle file permissions and access
4. Process files even when no user is logged in

## Troubleshooting

### Common Issues:

1. **"CSV input directory does not exist"**
   - The service will create directories automatically
   - Check file permissions if on a restricted system

2. **"No CSV files found"**
   - Ensure files have `.csv` extension
   - Check that files are in the correct input directory

3. **"Invalid Georgian phone number format"**
   - Verify phone numbers follow Georgian format (9 digits starting with 5)
   - Check for extra characters or incorrect country codes

4. **"Permission denied"**
   - Ensure the service has read/write access to the CSV directories
   - Run as administrator if necessary 