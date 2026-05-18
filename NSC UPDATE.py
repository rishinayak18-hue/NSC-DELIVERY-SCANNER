import json
import os
import pandas as pd
import requests
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
    f"https://nsearchives.nseindia.com/"
    f"products/content/sec_bhavdata_full_{dd}{mon}{yyyy}.csv"
)

print(url)

# ---------------- REQUEST ---------------- #

headers = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64)"
    )
}

response = requests.get(
    url,
    headers=headers,
    timeout=30
)

print("STATUS:", response.status_code)

print(response.text[:500])

# ---------------- SAVE FILE ---------------- #

with open(
    "bhavcopy.csv",
    "w",
    encoding="utf-8"
) as f:

    f.write(response.text)

print("CSV SAVED")

# ---------------- READ CSV ---------------- #

try:

    df = pd.read_csv(
        "bhavcopy.csv",
        engine="python"
    )

    print("CSV LOADED")

except Exception as e:

    print("CSV ERROR:", e)

    sheet.update(
        "A1",
        [["CSV ERROR", str(e)]]
    )

    exit()

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

print("ROWS FOUND:", len(filtered))

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

print("GOOGLE SHEET UPDATED SUCCESSFULLY")
