import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import requests
import zipfile
import io
from datetime import datetime, timedelta
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
# FETCH NSE BHAVCOPY
# =========================================================

def fetch_bhavcopy(date_obj):

    date_str = date_obj.strftime("%Y%m%d")

    url = (
        f"https://nsearchives.nseindia.com/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{date_str}_F_0000.csv.zip"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
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
# FETCH DELIVERY DATA FROM NSE API
# =========================================================

def fetch_delivery(symbol):

    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "*/*",
        "Referer": "https://www.nseindia.com/"
    }

    try:

        session.get(
            "https://www.nseindia.com",
            headers=headers,
            timeout=20
        )

        url = (
            f"https://www.nseindia.com/api/"
            f"quote-equity?symbol={symbol}"
        )

        response = session.get(
            url,
            headers=headers,
            timeout=20
        )

        data = response.json()

        security_info = data.get(
            "securityWiseDP",
            {}
        )

        delivery_qty = security_info.get(
            "deliveryQuantity",
            0
        )

        delivery_pct = security_info.get(
            "deliveryToTradedQuantity",
            0
        )

        return delivery_qty, delivery_pct

    except Exception as e:

        print(
            "DELIVERY API ERROR:",
            symbol,
            e
        )

        return 0, 0

# =========================================================
# GET LATEST WORKING BHAVCOPY
# =========================================================

def get_latest_bhavcopy():

    today = datetime.now()

    for i in range(7):

        test_date = today - timedelta(days=i)

        if test_date.weekday() >= 5:
            continue

        df = fetch_bhavcopy(test_date)

        if df is not None:
            return df, test_date

    return None, None

# =========================================================
# FETCH DATA
# =========================================================

latest_bhav, working_date = get_latest_bhavcopy()

if latest_bhav is None:

    worksheet.update(
        'K2',
        [["BHAVCOPY FAILED"]]
    )

    raise Exception("BHAVCOPY FAILED")

# =========================================================
# COLUMN DETECTION
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

# =========================================================
# FILTER EQ STOCKS
# =========================================================

latest_bhav = latest_bhav[
    latest_bhav[series_col]
    .astype(str)
    .str.strip() == 'EQ'
]

# =========================================================
# REMOVE ETF
# =========================================================

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
# TOP 50 STOCKS
# =========================================================

top250 = latest_bhav.sort_values(
    by=vol_col,
    ascending=False
).head(50)

# =========================================================
# PREPARE DATA
# =========================================================

rows = []

for _, row in top250.iterrows():

    try:

        symbol = row[sym_col]

        cmp_price = row[close_col]

        volume = row[vol_col]

        turnover = 0

        if pd.notna(volume) and pd.notna(cmp_price):

            turnover = round(
                (float(volume) * float(cmp_price)) / 10000000,
                2
            )

        # DELIVERY API
        delivery_qty, delivery_pct = fetch_delivery(symbol)

        rows.append([
            str(symbol),
            float(cmp_price) if pd.notna(cmp_price) else 0,
            float(volume) if pd.notna(volume) else 0,
            float(delivery_qty),
            float(delivery_pct),
            float(turnover)
        ])

    except Exception as e:

        print("ROW ERROR:", e)

# =========================================================
# REMOVE NaN / INF
# =========================================================

rows = np.nan_to_num(rows).tolist()

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
