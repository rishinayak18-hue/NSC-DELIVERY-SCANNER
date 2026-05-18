import json
import os
import pandas as pd
import requests
import io
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- GOOGLE CREDENTIALS ---------------- #

creds_dict = json.loads(
    os.environ["GOOGLE_CREDENTIALS"]
)

with open("credentials.json", "w") as f:
    json.dump(creds_dict, f)

print("Credentials Loaded")

# ---------------- GOOGLE AUTH ---------------- #

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json",
    scope
)

client = gspread.authorize(creds)

print("Google Authorized")

# ---------------- OPEN SHEET ---------------- #

spreadsheet = client.open("NSE Delivery Scanner")

print("Spreadsheet Opened")

sheet = spreadsheet.sheet1

print("Sheet Selected")

# ---------------- TEST WRITE ---------------- #

sheet.update(
    "A1",
    [["TEST SUCCESS"]]
)

print("Test Write Done")


