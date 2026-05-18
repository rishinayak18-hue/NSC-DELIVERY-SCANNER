import json
import os
import pandas as pd
import requests
import io
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- SECRET TO JSON FILE ---------------- #

creds_dict = json.loads(
    os.environ["GOOGLE_CREDENTIALS"]
)

with open("credentials.json", "w") as f:
    json.dump(creds_dict, f)

# ---------------- GOOGLE SHEET ---------------- #

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json",
    scope
)

client = gspread.authorize(creds)

sheet = client.open("NSE Delivery Scanner").sheet1

# ---------------- NSE FETCH ---------------- #

today = datetime.now()

dd = today.strftime("%d")
mon = today.strftime("%b").upper()
yyyy = today.strftime("%Y")

url = (
    f"https://archives.nseindia.com/products/content/"
    f"sec_bhavdata_full_{dd}{mon}{yyyy}.csv"
)

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(url, headers=headers)

df = pd.read_csv(io.StringIO(r.text))

df.columns = df.columns.str.strip()

watchlist = ["RELIANCE", "TCS", "INFY"]

filtered = df[
    df["SYMBOL"].str.strip().isin(watchlist)
]

rows = []

for _, row in filtered.iterrows():

    rows.append([
        row["SYMBOL"],
        row["CLOSE_PRICE"],
        row["DELIV_PER"]
    ])

sheet.clear()

sheet.update(
    [["Stock", "CMP", "Delivery %"]] + rows
)

print("Google Sheet Updated")