import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import requests
import zipfile
import io
from datetime import datetime
import os
import json

# =========================================================
# GOOGLE SHEET AUTH
# =========================================================

creds_json = os.environ.get('GCP_CREDENTIALS')

creds_dict = json.loads(creds_json)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict,
    scope
)

client = gspread.authorize(creds)

# =========================================================
# GOOGLE SHEET
# =========================================================

SPREADSHEET_ID = "10BXNfcfrQ7eznLUeaiRgL4zHFyLHKmWL1gEXULVeSEY"

worksheet = client.open_by_key(
    SPREADSHEET_ID
).worksheet("Sheet1")

# =========================================================
# FETCH UDIFF BHAVCOPY
# =========================================================

def fetch_bhavcopy(date_obj):

    date_str = date_obj.strftime("%Y%m%d")

    url = (
        f"https://nsearchives.nseindia.com/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{date_str}_F_0000.csv.zip"
    )

    headers = {
        "User-Agent":
        "Mozilla/5.0"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        print("BHAVCOPY STATUS:", response.status_code)

        if response.status_code != 200:
            return None

        with zipfile.ZipFile(
            io.BytesIO(response.content)
        ) as z:

            csv_filename = z.namelist()[0]

            with z.open(csv_filename) as f:

                df = pd.read_csv(f)

                return df

    except Exception as e:

        print("BHAVCOPY ERROR:", e)

        return None

# =========================================================
# FETCH DELIVERY DATA
# =========================================================

def fetch_delivery_data(date_obj):

    dd = date_obj.strftime("%d")

    mon = date_obj.strftime("%b").upper()

    yyyy = date_obj.strftime("%Y")

    url = (
        f"https://nsearchives.nseindia.com/products/content/"
        f"sec_bhavdata_full_{dd}{mon}{yyyy}.csv"
    )

    headers = {
        "User-Agent":
        "Mozilla/5.0"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        print("DELIVERY STATUS:", response.status_code)

        if response.status_code != 200:
            return None

        if "SYMBOL" not in response.text:
            return None

        df = pd.read_csv(
            io.StringIO(response.text)
        )

        df.columns = df.columns.str.strip()

        return df

    except Exception as e:

        print("DELIVERY ERROR:", e)

        return None

# =========================================================
# FIXED WORKING DATE
# =========================================================

working_date = datetime(2025, 5, 16)

latest_bhav = fetch_bhavcopy(
    working_date
)

latest_delivery = fetch_delivery_data(
    working_date
)

# =========================================================
# CHECK DATA
# =========================================================

if latest_bhav is None:

    worksheet.update(
        'K2',
        [["BHAVCOPY FAILED"]]
    )

    raise Exception("BHAVCOPY FAILED")

if latest_delivery is None:

    worksheet.update(
        'K2',
        [["DELIVERY FAILED"]]
    )

    raise Exception("DELIVERY FAILED")

# =========================================================
# CLEAN BHAVCOPY
# =========================================================

sym_col = (
    'TckrSymb'
    if 'TckrSymb' in latest_bhav.columns
    else 'SYMBOL'
)

close_col = (
    'ClsPric'
    if 'ClsPric' in latest_bhav.columns
    else 'CLOSE'
)

series_col = (
    'SctySrs'
    if 'SctySrs' in latest_bhav.columns
    else 'SERIES'
)

vol_col = None

for c in [
    'TtlTradgVol',
    'TtlTrdQty',
    'TotTrdQty',
    'TOTTRDQTY'
]:

    if c in latest_bhav.columns:

        vol_col = c

        break

# EQ only

latest_bhav = latest_bhav[
    latest_bhav[series_col]
    .astype(str)
    .str.strip() == 'EQ'
]

# Remove ETFs

filter_keywords = (
    'BEES|ETF|GOLD|LIQUID|CASE|SILVER|LIQ'
)

latest_bhav = latest_bhav[
    ~latest_bhav[sym_col]
    .astype(str)
    .str.contains(
        filter_keywords,
        case=False,
        na=False
    )
]

# =========================================================
# TOP 250 STOCKS
# =========================================================

top250 = latest_bhav.sort_values(
    by=vol_col,
    ascending=False
).head(250)

# =========================================================
# CLEAN DELIVERY DATA
# =========================================================

latest_delivery["SYMBOL"] = (
    latest_delivery["SYMBOL"]
    .astype(str)
    .str.strip()
)

# =========================================================
# MERGE
# =========================================================

merged = pd.merge(
    top250,
    latest_delivery,
    left_on=sym_col,
    right_on="SYMBOL",
    how="left"
)

# =========================================================
# PREPARE FINAL DATA
# =========================================================

rows = []

for _, row in merged.iterrows():

    try:

        symbol = row[sym_col]

        cmp_price = row[close_col]

        volume = row[vol_col]

        delivery_qty = row["DELIV_QTY"]

        delivery_pct = row["DELIV_PER"]

        turnover = round(
            float(row["TTL_TRD_VAL"]) / 10000000,
            2
        )

        rows.append([
            symbol,
            cmp_price,
            volume,
            delivery_qty,
            delivery_pct,
            turnover
        ])

    except Exception as e:

        print("ROW ERROR:", e)

# =========================================================
# UPDATE SHEET
# =========================================================

worksheet.batch_clear(['A2:F1000'])

worksheet.update(
    'A2',
    rows
)

# =========================================================
# STATUS
# =========================================================

status_msg = (
    f"Updated Successfully : "
    f"{working_date.strftime('%d-%b-%Y')}"
)

worksheet.update(
    'K2',
    [[status_msg]]
)

print("SUCCESS : GOOGLE SHEET UPDATED")
