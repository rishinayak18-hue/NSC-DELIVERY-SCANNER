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

# ---------------- WORKING FILE URL ---------------- #

url = (
    "https://nsearchives.nseindia.com/"
    "products/content/sec_bhavdata_full_16MAY2025.csv"
)

print(url)

# ---------------- REQUEST ---------------- #

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    url,
    headers=headers,
    timeout=30
)

print("STATUS:", response.status_code)

# ---------------- SAVE RAW ---------------- #

with open(
    "bhavcopy.csv",
    "w",
    encoding="utf-8"
) as f:

    f.write(response.text)

# ---------------- READ CSV ---------------- #

try:

    df = pd.read_csv(
        "bhavcopy.csv",
        sep=",",
        engine="python",
        on_bad_lines="skip"
    )

except Exception as e:

    sheet.update(
        "A1",
        [["CSV ERROR", str(e)]]
    )

    raise

print(df.head())

# ---------------- CLEAN ---------------- #

df.columns = df.columns.str.strip()

if "SYMBOL" not in df.columns:

    sheet.update(
        "A1",
        [["INVALID NSE RESPONSE"]]
    )

    print("INVALID RESPONSE")

    exit()

watchlist = [
    "RELIANCE",
    "TCS",
    "INFY",
    "SBIN"
]

df["SYMBOL"] = (
    df["SYMBOL"]
    .astype(str)
    .str.strip()
)

filtered = df[
    df["SYMBOL"].isin(watchlist)
]

print(filtered)

# ---------------- ROWS ---------------- #

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

    except:
        pass

# ---------------- SHEET UPDATE ---------------- #

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
