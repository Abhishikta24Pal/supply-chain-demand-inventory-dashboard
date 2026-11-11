"""
Supply Chain Mock Data Generator
--------------------------------
Creates 5 CSV files AND a SQLite database (supply_chain.db) with realistic,
deliberately MESSY supply chain data for the Power BI portfolio project.

Run:  python generate_supply_chain_data.py
Needs: pip install pandas numpy
"""
import os
import sqlite3

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# 0. Setup
# ----------------------------------------------------------------------------
rng = np.random.default_rng(42)  # fixed seed = everyone gets the same data

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supply_chain_data")
os.makedirs(OUT_DIR, exist_ok=True)

START = pd.Timestamp("2025-01-01")
months = pd.date_range("2025-01-01", "2026-10-01", freq="MS")  # 22 months
N_M = len(months)

# ----------------------------------------------------------------------------
# 1. Products (60 items, 6 categories)
# ----------------------------------------------------------------------------
CATALOG = {
    "Electronics": dict(
        items=["Wireless Earbuds", "Bluetooth Speaker", "Power Bank", "USB-C Cable",
               "Smart Watch", "Webcam", "Keyboard", "Mouse", "Phone Charger", "LED Monitor"],
        cost=(300, 6000), bias=0.12, shelf=None),
    "Home & Kitchen": dict(
        items=["Air Fryer", "Mixer Grinder", "Water Bottle", "Lunch Box", "Non-stick Pan",
               "Electric Kettle", "Storage Jar Set", "Dinner Set", "Knife Set", "Cutting Board"],
        cost=(150, 3500), bias=0.0, shelf=None),
    "Apparel": dict(
        items=["Cotton T-Shirt", "Denim Jeans", "Hoodie", "Running Shoes", "Formal Shirt",
               "Track Pants", "Socks Pack", "Winter Jacket", "Kurta", "Cap"],
        cost=(100, 2500), bias=0.05, shelf=None),
    "Grocery": dict(
        items=["Basmati Rice 5kg", "Olive Oil 1L", "Green Tea Box", "Instant Noodles Case",
               "Almonds 500g", "Peanut Butter", "Masala Chai Pack", "Cereal Box",
               "Honey Jar", "Pasta Pack"],
        cost=(60, 700), bias=-0.10, shelf=[180, 270, 365]),
    "Health & Beauty": dict(
        items=["Face Wash", "Sunscreen", "Shampoo", "Body Lotion", "Vitamin C Tablets",
               "Hand Sanitizer", "Hair Oil", "Lip Balm", "Protein Powder", "Toothpaste Pack"],
        cost=(80, 1800), bias=-0.05, shelf=[365, 540, 730]),
    "Office Supplies": dict(
        items=["A4 Paper Ream", "Gel Pens Box", "Notebook Pack", "Stapler", "Desk Organizer",
               "Sticky Notes", "Marker Set", "File Folders", "Whiteboard", "Printer Ink"],
        cost=(50, 1500), bias=0.0, shelf=None),
}

plist = []
pid = 1
for cat, cfg in CATALOG.items():
    for name in cfg["items"]:
        cost = round(float(rng.uniform(*cfg["cost"])), 2)
        plist.append(dict(
            product_id=f"P{pid:03d}",
            product_name=name,
            category=cat,
            unit_cost=cost,
            unit_price=round(cost * float(rng.uniform(1.25, 1.6)), 2),
            shelf_life_days=int(rng.choice(cfg["shelf"])) if cfg["shelf"] else None,
            lead_time_days=int(rng.integers(3, 22)),
            _base=float(np.clip(rng.lognormal(2.2, 0.5), 3, 45)),
            _bias=cfg["bias"],
        ))
        pid += 1
prod = pd.DataFrame(plist)
nP = len(prod)

# ----------------------------------------------------------------------------
# 2. Warehouses (5 locations)
# ----------------------------------------------------------------------------
wh = pd.DataFrame([
    dict(warehouse_id="W01", warehouse_name="Delhi DC", city="Delhi", region="North", capacity_units=12000, _f=1.3),
    dict(warehouse_id="W02", warehouse_name="Mumbai DC", city="Mumbai", region="West", capacity_units=15000, _f=1.5),
    dict(warehouse_id="W03", warehouse_name="Bengaluru DC", city="Bengaluru", region="South", capacity_units=11000, _f=1.2),
    dict(warehouse_id="W04", warehouse_name="Kolkata DC", city="Kolkata", region="East", capacity_units=8000, _f=0.8),
    dict(warehouse_id="W05", warehouse_name="Hyderabad DC", city="Hyderabad", region="South", capacity_units=9000, _f=0.9),
])
nW = len(wh)

# ----------------------------------------------------------------------------
# 3. Hidden "story" behind each product-warehouse pair
# ----------------------------------------------------------------------------
SEASON = np.array([0.90, 0.85, 0.90, 0.95, 1.00, 0.95, 0.95, 1.00, 1.05, 1.20, 1.30, 1.20])

expected = np.zeros((nP, nW, N_M))
for mi, m in enumerate(months):
    expected[:, :, mi] = (prod["_base"].values[:, None] * wh["_f"].values[None, :]
                          * SEASON[m.month - 1] * (1.01 ** mi))

behaviour = rng.choice(["normal", "excess", "shortage", "stale"],
                       size=(nP, nW), p=[0.68, 0.12, 0.12, 0.08])
cutoff = rng.integers(4, 16, size=(nP, nW))  # month when 'stale' items stop moving

# ----------------------------------------------------------------------------
# 4. Sales (daily transactions)
# ----------------------------------------------------------------------------
s_date, s_pid, s_wid, s_qty = [], [], [], []
actual = np.zeros((nP, nW, N_M))

for pi in range(nP):
    for wi in range(nW):
        for mi, m in enumerate(months):
            days = pd.date_range(m, m + pd.offsets.MonthEnd(0))
            mult = 0.15 if (behaviour[pi, wi] == "stale" and mi >= cutoff[pi, wi]) else 1.0
            q = rng.poisson(expected[pi, wi, mi] * mult / len(days), size=len(days))
            actual[pi, wi, mi] = q.sum()
            nz = np.flatnonzero(q)
            s_date.extend(days[nz])
            s_pid.extend([prod.product_id[pi]] * len(nz))
            s_wid.extend([wh.warehouse_id[wi]] * len(nz))
            s_qty.extend(q[nz].tolist())

sales = pd.DataFrame(dict(order_date=s_date, product_id=s_pid, warehouse_id=s_wid, quantity=s_qty))
sales = sales.sort_values("order_date", kind="stable").reset_index(drop=True)
sales.insert(0, "sale_id", [f"S{i:06d}" for i in range(1, len(sales) + 1)])
price_map = dict(zip(prod.product_id, prod.unit_price))
sales["unit_price"] = (sales.product_id.map(price_map)
                       * rng.uniform(0.95, 1.05, len(sales))).round(2)

# ----------------------------------------------------------------------------
# 5. Inventory (month-end snapshots)
# ----------------------------------------------------------------------------
inv_rows = []
for pi in range(nP):
    for wi in range(nW):
        avg = expected[pi, wi, :].mean()
        beh = behaviour[pi, wi]
        stock = avg * (0.8 if beh == "shortage" else 1.5)
        last_recv = START - pd.Timedelta(days=int(rng.integers(5, 25)))
        for mi, m in enumerate(months):
            sold = actual[pi, wi, mi]
            recv = 0.0
            if beh == "normal":
                if stock < avg:
                    recv = 2 * avg - stock
            elif beh == "excess":
                recv = 1.8 * avg
            elif beh == "shortage":
                recv = 0.7 * sold if mi % 2 == 0 else 0.0
            elif beh == "stale":
                if mi < cutoff[pi, wi]:
                    recv = (2 * avg - stock) if stock < avg else 0.0
                elif mi == cutoff[pi, wi]:
                    recv = 4 * avg
            if recv > 0:
                last_recv = m + pd.Timedelta(days=int(rng.integers(0, m.days_in_month)))
            stock = max(0.0, stock + recv - sold)
            inv_rows.append((m + pd.offsets.MonthEnd(0), prod.product_id[pi],
                             wh.warehouse_id[wi], int(round(stock)), last_recv))

inventory = pd.DataFrame(inv_rows, columns=["snapshot_date", "product_id", "warehouse_id",
                                            "units_on_hand", "last_received_date"])

# ----------------------------------------------------------------------------
# 6. Forecast vs actual (monthly)
# ----------------------------------------------------------------------------
f_rows = []
for pi in range(nP):
    bias = prod._bias[pi]
    for wi in range(nW):
        for mi, m in enumerate(months):
            fc = expected[pi, wi, mi] * (1 + bias + rng.normal(0, 0.15))
            f_rows.append((m, prod.product_id[pi], wh.warehouse_id[wi],
                           max(0, int(round(fc))), int(actual[pi, wi, mi])))
forecast = pd.DataFrame(f_rows, columns=["forecast_month", "product_id", "warehouse_id",
                                         "forecast_qty", "actual_qty"])

# ----------------------------------------------------------------------------
# 7. Make the data realistically MESSY (we will clean it in Milestone 1)
# ----------------------------------------------------------------------------
# --- sales
s = sales.copy()
s["quantity"] = s["quantity"].astype("Int64")
n = len(s)
dups = s.sample(frac=0.015, random_state=1)
i_low = s.sample(frac=0.02, random_state=2).index
i_space = s.sample(frac=0.015, random_state=3).index
i_null_q = s.sample(frac=0.005, random_state=4).index
i_neg = s.sample(frac=0.003, random_state=5).index
i_null_w = s.sample(frac=0.005, random_state=6).index
i_big = s.sample(n=3, random_state=7).index
s.loc[i_low, "product_id"] = s.loc[i_low, "product_id"].str.lower()
s.loc[i_space, "product_id"] = " " + s.loc[i_space, "product_id"] + " "
s.loc[i_null_q, "quantity"] = pd.NA
s.loc[i_neg, "quantity"] = -s.loc[i_neg, "quantity"]
s.loc[i_null_w, "warehouse_id"] = np.nan
s.loc[i_big, "quantity"] = 9999
s = pd.concat([s, dups]).sort_values("sale_id", kind="stable").reset_index(drop=True)
s["order_date"] = pd.to_datetime(s["order_date"]).dt.strftime("%Y-%m-%d")

# --- products
p = prod.drop(columns=["_base", "_bias"]).copy()
p["shelf_life_days"] = p["shelf_life_days"].astype("Int64")
p.loc[[3, 14, 27, 41], "category"] = ["electronics", "Home & Kitchen ", "APPAREL", "grocery "]
p.loc[[8, 33], "unit_cost"] = np.nan
p = pd.concat([p, p.iloc[[20]]]).reset_index(drop=True)

# --- inventory
inv = inventory.copy()
inv["units_on_hand"] = inv["units_on_hand"].astype("Int64")
i_negs = inv.sample(frac=0.01, random_state=11).index
i_nulld = inv.sample(frac=0.005, random_state=12).index
inv_dups = inv.sample(frac=0.003, random_state=13)
inv.loc[i_negs, "units_on_hand"] = -inv.loc[i_negs, "units_on_hand"].abs()
inv["snapshot_date"] = inv["snapshot_date"].dt.strftime("%Y-%m-%d")
inv["last_received_date"] = pd.to_datetime(inv["last_received_date"]).dt.strftime("%Y-%m-%d")
inv.loc[i_nulld, "last_received_date"] = np.nan
inv = pd.concat([inv, inv_dups.assign(
    snapshot_date=inv_dups.snapshot_date.dt.strftime("%Y-%m-%d"),
    last_received_date=pd.to_datetime(inv_dups.last_received_date).dt.strftime("%Y-%m-%d"))]
).reset_index(drop=True)

# --- forecast
f = forecast.copy()
f["forecast_qty"] = f["forecast_qty"].astype("Int64")
f_null = f.sample(frac=0.005, random_state=21).index
f_dups = f.sample(frac=0.003, random_state=22)
f.loc[f_null, "forecast_qty"] = pd.NA
f = pd.concat([f, f_dups]).reset_index(drop=True)
f["forecast_month"] = pd.to_datetime(f["forecast_month"]).dt.strftime("%Y-%m-%d")

w = wh.drop(columns=["_f"]).copy()

# ----------------------------------------------------------------------------
# 8. Save CSVs + SQLite database
# ----------------------------------------------------------------------------
tables = {"products": p, "warehouses": w, "sales": s, "inventory": inv, "forecast": f}

for name, df in tables.items():
    df.to_csv(os.path.join(OUT_DIR, f"{name}.csv"), index=False)

db_path = os.path.join(OUT_DIR, "supply_chain.db")
if os.path.exists(db_path):
    os.remove(db_path)
con = sqlite3.connect(db_path)
for name, df in tables.items():
    df.to_sql(name, con, index=False)
con.close()

print("\nDone! Files saved in:", OUT_DIR)
print("-" * 40)
for name, df in tables.items():
    print(f"{name + '.csv':<16}{len(df):>8,} rows")
print(f"{'supply_chain.db':<16}   (same 5 tables, raw/messy)")
