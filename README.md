# Supply Chain Demand & Inventory Analytics Dashboard

A Power BI project that looks at demand, stock levels and forecast accuracy across five warehouses, and flags products that are running short, overstocked or sitting on the shelf too long.

I built this to practise the full analyst workflow end to end: messy data in, clear recommendations out.

**Status:** In progress. Data preparation is done and the dashboard is being built.

## About the data

The data is **synthetic**. Real supply chain data is confidential, so I wrote a Python script that generates 22 months of sales, inventory and forecast data for 60 products across 5 warehouses (January 2025 to October 2026).

I deliberately created problems into it: duplicates, missing values, inconsistent text and impossible values like negative stock. I also built in stockouts, overstock and slow-moving items, so the dashboard has real patterns to find. The numbers are made up, so none of the findings describe a real business.

## Tools

Python (data generation)
SQL / SQLite (profiling and cleaning)
Power Query (shaping) 
Power BI and DAX (model, measures, dashboard)

## Progress

- [x] Generate the dataset (Python)
- [x] Profile and clean the data (SQL)
- [x] Shape and type the data (Power Query)
- [ ] Data model: star schema and date table
- [ ] DAX measures: stock level, inventory turnover, MAE, MAPE, forecast accuracy
- [ ] Dashboard: KPIs, shortage / excess / aged inventory flags, monthly demand trends
- [ ] Findings and recommendations

## What I cleaned, and how
I profiled each table first and then cleaned it, so every fix is based on a measured problem.

| Problem found | Count | What I did |
|---|---|---|
| Duplicate sales rows | 934 | Kept one row per sale ID |
| Product IDs with wrong case or spaces | 2,167 | Standardised (192 variants became 60 products) |
| Missing quantity or warehouse in sales | 312 + 309 | Removed, because they can't be estimated reliably |
| Negative quantities or stock | 186 sales, 47 stock | Treated as sign errors and made positive |
| Extreme quantities (over 1,000 units) | 3 | Removed as typos |
| Messy category names | 10 spellings, 6 real categories | Standardised |
| Missing forecast values | 33 | Removed |
| Missing last-received dates | 33 | Filled from the previous month within each product and warehouse |

**Assumption to note:** I treated negative values as data-entry errors. In a real project I would confirm with the data owner, because negative sales can also mean returns.

## Project structure

```
├── python/   data generator script
├── data/     raw generated data (CSV + SQLite database)
│   └── clean/    cleaned tables used by Power BI
├── sql/      profiling and cleaning queries
├── powerbi/  Power BI report file
└── docs/     screenshots and notes
```

## Run it yourself

1. `pip install pandas numpy`
2. `python python/generate_supply_chain_data.py` (the data is created in a `supply_chain_data` folder next to the script)
3. Open the database in DB Browser for SQLite and run `sql/01_data_profiling.sql`, then `sql/02_data_cleaning.sql`
4. Export the `clean_` tables to CSV and open `powerbi/Supply_Chain_Dashboard.pbix`

## Author

Abhishikta