# APK VT Scanner

This project is designed to scan APK files and generate a detailed report using VirusTotal. The report includes scan results from various antivirus engines and a breakdown of the permissions required by the APK.

## Features

- **VirusTotal Integration**: Automatically scans APK files and retrieves detection results from VirusTotal.
- **Permissions Analysis**: Extracts and lists all permissions requested by the APK.
- **Detailed Reporting**: Combines scan results and permissions information into a comprehensive report.

## Prerequisites

- Python 3.x
- VirusTotal API key

## Execution


   ```bash
   python VTScanner.py <Input Path> <Scan Results.xlsx> <Permission.xlsx>
