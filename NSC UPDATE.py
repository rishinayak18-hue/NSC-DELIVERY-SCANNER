import json
import os
import pandas as pd
import requests
import io
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- GOOGLE AUTH ---------------- #

creds_dict = json.loads(
    os.environ["GOOGLE_CREDENTIALS"]
)

with open("credentials.json", "w") as f:
    json.dump(creds_dict, f)

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

# ---------------- NSE SESSION ---------------- #

session = requests.Session()

headers = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com/"
}

# First get cookies

session.get(
    "https://www.nseindia.com",
    headers=headers,
    timeout=20
)

# ---------------- NSE CSV URL ---------------- #

url = (
    "https://nsearchives.nseindia.com/"
    "products/content/sec_bhavdata_full_16MAY2025.csv"
)

response = session.get(
    url,
    headers=headers,
    timeout=30
)

print(response.status_code)

print(response.text[:300])

# ---------------- CHECK RESPONSE ---------------- #

if "SYMBOL" not in response.text:

    sheet.update(
        "A1",
        [["NSE BLOCKED OR INVALID RESPONSE"]]
    )

    exit()

# ---------------- READ CSV ---------------- #

df = pd.read_csv(
    io.StringIO(response.text)
)

df.columns = df.columns.str.strip()

df["SYMBOL"] = (
    df["SYMBOL"]
    .astype(str)
    .str.strip()
)

# ---------------- WATCHLIST ---------------- #

watchlist = [
    "RELIANCE",
    "TCS",
    "INFY",
    "SBIN"
]

filtered = df[
    df["SYMBOL"].isin(watchlist)
]

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
