from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd

def add_full_address(df):
    df['Full Address'] = df['Address'] + ', ' + df['Country Secondary Subdivision'] + ', ' + df['Country']
    return df

def geocode_addresses(df):
    geolocator = Nominatim(user_agent="geocoder", timeout=10)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    df["location"] = df["Full Address"].apply(geocode)
    df["lat"] = df["location"].apply(lambda x: x.latitude if x else None)
    df["lon"] = df["location"].apply(lambda x: x.longitude if x else None)
    return df

def create_buffers(df):
    geometry = [Point(xy) for xy in zip(df['lon'], df['lat'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    gdf_proj = gdf.to_crs(epsg=3857)
    gdf_proj['geometry_5km'] = gdf_proj.geometry.buffer(5000)
    gdf_proj['geometry_10km'] = gdf_proj.geometry.buffer(10000)
    gdf_buffers = gdf_proj.to_crs(epsg=4326)
    return gdf_buffers
