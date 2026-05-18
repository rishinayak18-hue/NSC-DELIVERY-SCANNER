import json
import os
import pandas as pd
import requests
import io
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

print("START")

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

sheet = client.open(
    "NSE Delivery Scanner"
).sheet1

print("Google Sheet Connected")

# ---------------- NSE URL ---------------- #

today = datetime(2025, 5, 16)

dd = today.strftime("%d")
mon = today.strftime("%b").upper()
yyyy = today.strftime("%Y")

url = (
    f"https://archives.nseindia.com/products/content/"
    f"sec_bhavdata_full_{dd}{mon}{yyyy}.csv"
)

print(url)

# ---------------- REQUEST ---------------- #

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    url,
    headers=headers,
    timeout=20
)

print("STATUS:", response.status_code)

# ---------------- SAVE RAW CSV ---------------- #

with open("test.csv", "w", encoding="utf-8") as f:
    f.write(response.text)

print("CSV Saved")

# ---------------- READ CSV ---------------- #

try:

    df = pd.read_csv("test.csv")

    print("CSV Loaded")

except Exception as e:

    print("CSV ERROR:", e)

    sheet.update(
        "A1",
        [["CSV ERROR", str(e)]]
    )

    exit()

# ---------------- CLEAN ---------------- #

df.columns = df.columns.str.strip()

df["SYMBOL"] = (
    df["SYMBOL"]
    .astype(str)
    .str.strip()
)

watchlist = [
    "RELIANCE",
    "TCS",
    "INFY",
    "SBIN"
]

filtered = df[
    df["SYMBOL"].isin(watchlist)
]

print(filtered)

# ---------------- PREPARE ROWS ---------------- #

rows = []

for _, row in filtered.iterrows():

    try:

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

    except Exception as e:

        print("ROW ERROR:", e)

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

print("DONE")
