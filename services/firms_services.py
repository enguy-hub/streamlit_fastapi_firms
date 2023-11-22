from datetime import date
from functools import lru_cache

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from streamlit_folium import st_folium


"""""" """""" """""" """""" """""" """""" """""" """""" """""" """""" """""
    Services for getting/processing FIRMS data from NASA FIRMS API
""""" """""" """""" """""" """""" """""" """""" """""" """""" """""" """"""

FIRMS_API_URL = "https://firms.modaps.eosdis.nasa.gov"
FIRMS_API_KEY = "YOUR_FIRMS_API_KEY_HERE"


def get_account_status(map_key: str = FIRMS_API_KEY):
    status_url = f"{FIRMS_API_URL}/mapserver/mapkey_status/?MAP_KEY={map_key}"

    try:
        df = pd.read_json(status_url, typ="series")

    except ValueError:
        # possible error, wrong MAP_KEY value, check for extra quotes, missing letters
        print(
            "There is an issue with the query. \nTry in your browser: %s" % status_url
        )

    return df


def get_current_transaction_count(map_key: str = FIRMS_API_KEY):
    status_url = f"{FIRMS_API_URL}/mapserver/mapkey_status/?MAP_KEY={map_key}"

    count = 0
    try:
        df = pd.read_json(status_url, typ="series")
        count = df["current_transactions"]

    except ValueError:
        print("Error in our call.")

    return count


def create_firms_csv_url(
    product: str, 
    country: str,
    days_ago: int,
) -> str:

    firms_csv_data_url = (
        f"{FIRMS_API_URL}/api/country/csv/{FIRMS_API_KEY}/{product}/{country}/{days_ago}"
    )

    return firms_csv_data_url


@lru_cache
def convert_firms_csv_to_gdf(firms_csv_data_url: str) -> gpd.GeoDataFrame:
    """
    Converts FIRMS API CSV data to a GeoDataFrame and calculates the centroid of the geodataframe.

    Parameters:
    ----------
    firms_csv_data_url : str
        URL of the CSV data from the FIRMS API.

    Returns:
    -------
    GeoDataFrame
        Geodataframe of the query result.
    list
        Coordinates [latitude, longitude] of the centroid of the geodataframe.
    """
    
    try:
        df = pd.read_csv(firms_csv_data_url)
    except Exception as e:
        raise Exception(f"Error reading CSV data: {e}")

    try:
        df = process_dataframe(df)
        df_filtered = filter_high_confidence(df)
        gdf = create_geodataframe(df_filtered)
        centroid_coords = calculate_centroid(gdf)

        return gdf, centroid_coords
    
    except Exception as e:
        raise Exception(f"Error processing data: {e}")


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Data processing steps
    
    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"] + " " + df["acq_time"].astype(str).str.zfill(4),
        format="%Y-%m-%d %H%M",
    )
    df["acq_datetime"] = df["acq_datetime"].dt.strftime("%Y-%m-%d %H%M")

    df["acq_date"] = pd.to_datetime(df["acq_date"], format="%Y-%m-%d")

    if df["acq_date"].max() == pd.Timestamp(date.today()):
        df["days_ago"] = (
            df["acq_date"].rank(method="dense", ascending=False).astype(int) - 1
        )
    else:
        df["days_ago"] = (
            df["acq_date"].rank(method="dense", ascending=False).astype(int)
        )

    df["acq_date"] = df["acq_date"].dt.strftime("%Y-%m-%d")
    
    # print ('Collected datetime: %s to %s' % (str(df['acq_datetime'].min()), str(df['acq_datetime'].max())))
    return df


def filter_high_confidence(df: pd.DataFrame) -> pd.DataFrame:
    
    df['high_confidence'] = False
    
    # Mark the rows that meet the confidence criteria
    if pd.api.types.is_numeric_dtype(df["confidence"]):
        df.loc[df["confidence"] >= 70, "high_confidence"] = True
        
    elif pd.api.types.is_string_dtype(df["confidence"]):
        df.loc[
            df["confidence"].isin(["n", "h"]), "high_confidence"
        ] = True
        
    df = df.drop(df[df["high_confidence"] == False].index).copy()
    
    return df


def create_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    # Convert DataFrame to GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs="EPSG:4326"
    )

    return gdf
    

def calculate_centroid(gdf: gpd.GeoDataFrame) -> list:
    # Calculate the centroid of the GeoDataFrame

    gdf = gdf.to_crs(epsg=4326)

    gdf_centroid = gdf.to_crs("+proj=cea").centroid.to_crs(gdf.crs)
    gdf_centroid = gdf_centroid.total_bounds
    # print(gdf_centroid, "\n")

    center_x = (gdf_centroid[0] + gdf_centroid[2]) / 2  # Average of minx and maxx
    center_y = (gdf_centroid[1] + gdf_centroid[3]) / 2  # Average of miny and maxy

    return [center_y, center_x]


def display_firms_points(gdf: gpd.GeoDataFrame, centroid: np.ndarray) -> st_folium:
    """
    Function to display the map of the geodataframe

    Parameters:
    ----------
        gdf: geodataframe - geodataframe of the query result
        centroid: narray - array of the coordinates of the centroid of the geodataframe

    Returns:
    -------
        st_map: streamlit-folium map - map of the geodataframe
    """

    foliumMap = folium.Map(location=centroid, zoom_start=5, tiles="CartoDB positron")

    colors = [
        "darkred",
        "red",
        "darkorange",
        "orange",
        "orange",
        "gray",
        "beige",
        "beige",
        "lightgray",
        "lightgray",
    ]

    # Add a marker for each point in the data, with a color based on datetime_rank
    folium.GeoJson(
        gdf,
        marker=folium.Marker(icon=folium.Icon(icon="fire", color="gray")),
        tooltip=folium.GeoJsonTooltip(
            fields=["acq_datetime", "confidence", "days_ago"],
            aliases=["Fire Detected On: ", "Detection Confidence: ", "Days Ago: "],
        ),
        style_function=lambda x: {
            "markerColor": colors[x["properties"]["days_ago"]]
            if x["properties"]["days_ago"] is not None
            else "gray"
        },
    ).add_to(foliumMap)

    st_map = st_folium(foliumMap, width=800, height=500)

    return st_map
