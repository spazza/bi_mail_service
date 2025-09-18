## BI Mail Service

Send automatic emails with BI reports attached. This library is designed to work with Power BI reports exported as PDF files and then stored in Microsoft
SharePoint. The PDF reports are downloaded using Microsoft Graph API and then sent as email attachments.

Since power BI when exporting to PDF saves the file with a timestamp in the name, the script looks for the today's date in the filename to find the correct report.

### Features

- Download PDF reports from SharePoint using Microsoft Graph API.
- Send emails with the downloaded reports as attachments.
- Configurable email subject, body, and recipient lists.
- Image extraction from PDF reports for embedding in email body.

### Usage

1. Configure the config.ini file with sharepoint settings and email server settings. An example `config.ini` file is provided in the `example/` folder.
2. Create a data folder in the root directory containing a number of subfolders equal to the number of reports you want to send. Each subfolder should contain:
   - `body.html`: HTML template for the email body.
   - `recipients.txt`: List of email recipients, one per line.
3. Create a script (e.g., `production.py` or `storage.py`) to call the `download_report` and `send_mail` functions with appropriate parameters.

Find some samples in the `example/` folder.

### Example

```python
from app.mail import send_mail
from app.download import download_report

download_report("Production Report", image_page=2)
send_mail("Production Report", subject="MyCompany Monthly Production Report")
```