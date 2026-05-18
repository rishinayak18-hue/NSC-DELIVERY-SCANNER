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

# ---------------- GOOGLE SHEET CONNECT ---------------- #

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

# ---------------- WATCHLIST ---------------- #

WATCHLIST = [
    "RELIANCE",
    "TCS",
    "INFY",
    "SBIN"
]

# ---------------- DATE ---------------- #

today = datetime.now()

dd = today.strftime("%d")
mon = today.strftime("%b").upper()
yyyy = today.strftime("%Y")

# ---------------- NSE URL ---------------- #

url = (
    f"https://archives.nseindia.com/products/content/"
    f"sec_bhavdata_full_{dd}{mon}{yyyy}.csv"
)

# ---------------- NSE SESSION ---------------- #

session = requests.Session()

headers = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

# First visit homepage for cookies

session.get(
    "https://www.nseindia.com",
    headers=headers,
    timeout=20
)

# Fetch bhavcopy

r = session.get(
    url,
    headers=headers,
    timeout=20
)

# ---------------- RESPONSE CHECK ---------------- #

if "SYMBOL" not in r.text:

    print("Invalid NSE response")
    print(r.text[:1000])

    exit()

# ---------------- READ CSV ---------------- #

df = pd.read_csv(
    io.StringIO(r.text)
)

df.columns = df.columns.str.strip()

df["SYMBOL"] = df["SYMBOL"].str.strip()

# ---------------- FILTER WATCHLIST ---------------- #

filtered = df[
    df["SYMBOL"].isin(WATCHLIST)
]

# ---------------- CREATE OUTPUT ---------------- #

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

# ---------------- GOOGLE SHEET UPDATE ---------------- #

headers_row = [[
    "Stock",
    "CMP",
    "Volume",
    "Delivery Qty",
    "Delivery %",
    "Turnover Cr"
]]

sheet.clear()

sheet.update(
    headers_row + rows
)

print("Google Sheet Updated Successfully")
