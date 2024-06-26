import pandas as pd
import geopandas as gpd

def bigmac():
    bigmac_data = pd.read_parquet("data/raw/bigmac_price.parquet")
    wage_data = pd.read_parquet("data/raw/wage.parquet")

    # Data Wrangling

    bigmac_data["year"] = pd.to_datetime(bigmac_data["date"]).dt.year

    # Using only the hourly wage data
    wage_data = wage_data[
        (wage_data["Pay period"] == "Hourly")
        & (wage_data["Series"] == "In 2022 constant prices at 2022 USD PPPs")
    ]

    bigmac_prepared = bigmac_data[["name", "year", "local_price", "dollar_price", "dollar_ex"]].copy()
    bigmac_prepared.rename(columns={"name": "country"}, inplace=True)

    wage_prepared = wage_data[["COUNTRY", "Country", "Time", "Value"]].copy()
    wage_prepared.rename(
        columns={"COUNTRY": "country_code", "Country": "country", "Time": "year", "Value": "usd_wage"},
        inplace=True,
    )

    # Ensure 'year' is integer for both datasets
    bigmac_prepared["year"] = bigmac_prepared["year"].astype(int)
    wage_prepared["year"] = wage_prepared["year"].astype(int)

    # Merge datasets on 'country' and 'year'
    merged_data = pd.merge(
        bigmac_prepared, wage_prepared, on=["country", "year"], how="inner"
    )

    # Calculate 'Big Macs per hour'
    merged_data["bigmacs_per_hour"] = (
        merged_data["usd_wage"] / merged_data["dollar_price"]
    )

    # Calculate Inflation
    bigmac_prepared.sort_values(by=["country", "year"], inplace=True)
    # Calculate the adjusted local_price based on the first year in record (2001)
    bigmac_prepared["multiplication_factor"] = bigmac_prepared.groupby("country")["local_price"].pct_change().fillna(0) + 1
    bigmac_prepared['cum_prod'] = bigmac_prepared.groupby('country')['multiplication_factor'].cumprod()

    # Merge
    merged_data = pd.merge(
        merged_data,
        bigmac_prepared[["country", "year", "cum_prod",]],
        on=["country", "year"],
        how="left",
    )
    merged_data['adjusted_usd_wage'] = merged_data['usd_wage'] / merged_data['cum_prod']
    merged_data['local_wage'] = merged_data['dollar_ex'] * merged_data['usd_wage']
    merged_data['adjusted_local_wage'] = merged_data['dollar_ex'] * merged_data['adjusted_usd_wage']

    merged_data.rename(
            columns={'adjusted_local_wage':'Adjusted Wage in Local Currency', 
                     'adjusted_usd_wage': 'Adjusted Wage in USD', 
                     'local_price': 'Bigmac Price in Local Currency', 
                     'dollar_price': 'Bigmac Price in USD',
                     'local_wage': 'Wage in Local Currency',
                     'usd_wage': 'Wage in USD'
                     },
            inplace=True,
        )
    # Saving the final dataset
    # merged_data.to_parquet("data/processed/merged_data_with_inflation.parquet", index=False)

    return merged_data

def geo():
    shapefile = 'data/raw/world-administrative-boundaries/world-administrative-boundaries.shp'
    gdf = gpd.read_file(shapefile)
    gdf.crs = 'EPSG:4326'
    return gdf