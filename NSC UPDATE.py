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

sheet = client.open(
    "NSE Delivery Scanner"
).sheet1

# ---------------- WATCHLIST ---------------- #

watchlist = [
    "RELIANCE",
    "TCS",
    "INFY",
    "SBIN"
]

# ---------------- FIXED WORKING DATE ---------------- #

today = datetime(2025, 5, 16)

dd = today.strftime("%d")
mon = today.strftime("%b").upper()
yyyy = today.strftime("%Y")

# ---------------- NSE URL ---------------- #

url = (
    f"https://archives.nseindia.com/products/content/"
    f"sec_bhavdata_full_{dd}{mon}{yyyy}.csv"
)

print(url)

# ---------------- NSE REQUEST ---------------- #

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(
    url,
    headers=headers,
    timeout=20
)

print("STATUS:", r.status_code)

# ---------------- CHECK RESPONSE ---------------- #

print(r.text[:500])

# ---------------- READ CSV ---------------- #

df = pd.read_csv(
    io.StringIO(r.text),
    skipinitialspace=True
)

# ---------------- CLEAN DATA ---------------- #

df.columns = df.columns.str.strip()

df["SYMBOL"] = (
    df["SYMBOL"]
    .astype(str)
    .str.strip()
)

# ---------------- FILTER ---------------- #

filtered = df[
    df["SYMBOL"].isin(watchlist)
]

print(filtered)

# ---------------- PREPARE DATA ---------------- #

rows = []

for _, row in filtered.iterrows():

    turnover = round(
        float(row["TTL_TRD_VAL"]) / 10000000,
        2
    )

    rows.append([
        row["SYMBOL"],
        row["CLOSE_PRICE"],
        row["TTL_TRD_QNTY"],
        row["DELIV_QTY"],
        row["DELIV_PER"],
        turnover
    ])

print(rows)

# ---------------- UPDATE SHEET ---------------- #

sheet.clear()

sheet.update(
    "A1",
    [[
        "Stock",
        "CMP",
        "Volume",
        "Delivery Qty",
        "Delivery %",
        "Turnover Cr"
    ]] + rows
)

print("GOOGLE SHEET UPDATED")
