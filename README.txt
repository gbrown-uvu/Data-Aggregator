Rush Power Sports LLC - eBay Data Aggregation Tool
Version: 1.0 (December 2025)
Purpose: Fetch eBay sales data, store it reliably, and generate detailed profit reports broken down by machine model and year.
Overview
This tool helps track which ATV/UTV parts and machines are selling best on eBay.
It pulls your recent sales, stores them in a local database, and creates a CSV report you can open in Excel or Google Sheets for easy analysis.
The report now shows:


Machine Name (e.g., Honda TRX250)
Year (e.g., 2001)
Tags used
Quantity sold
Revenue
eBay fees
Total Profit
Average days to sell


Sorted by highest profit first.
Files Included


Aggregation Tool.exe – The main program (double-click to run)
ebay_sales.db – Your sales database (grows over time – back this up regularly!)
ebay.yaml – eBay API credentials (keep secure)
stop_words.json – List of words ignored when identifying machine names (customizable)
favicon.ico – Custom icon (used for shortcuts)


How to Use


First Run
Double-click Aggregation Tool.exe
If missing, the tool will automatically create:
ebay_sales.db (empty database)
ebay.yaml (blank config template)




Set Up eBay API Credentials
Click the gear icon ⚙️ in the top-right
Go to the eBay API tab
Fill in:
App ID, Dev ID, Cert ID → Found at: https://developer.ebay.com/my/keys (Production section)
Auth Token → Generate a new one when needed (lasts ~18 months)


Click Save All


Update Info
Click Update Info button
Pulls your last 90 days of eBay sales
Adds any new sales to the database
Safe to run daily or weekly


Create File
Click Create File button
Choose where to save the report (defaults to Desktop)
Suggested name: ebay_machine_report_YYYYMMDD.csv
Open in Excel/Google Sheets to view sorted profits by machine + year


Customize Stop Words (Optional)
Gear icon → Stop Words tab
Type a word (case doesn't matter – it will be converted to uppercase)
Click Add to include it (e.g., "GRILL" to prevent misidentification)
Click Remove to delete an existing one
Click Save All to apply changes




Tips


Backupebay_sales.db regularly — it contains all your historical data
Run Update Info weekly to keep data current
When your Auth Token expires (every ~18 months), generate a new one and paste it in Settings
Create a desktop shortcut: Right-click the .exe → Send to → Desktop (create shortcut)
Then right-click shortcut → Properties → Change Icon → browse to favicon.ico
When adding ‘Stop Words’ to fix machine title issues, make sure to add the entire word you want it to stop at. For example, if the title is: 
1983 Honda ATC200X (SEAT, SADDLE) (MOUNTING BRACKET MOUNT LATCH A332
Then to stop at the correct spot, you would add  (SEAT,  to the list of stop words rather than just SEAT