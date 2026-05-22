from __future__ import annotations

from typing import Iterable
import warnings

import geopandas as gpd
import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from shapely.geometry import Point


def add_full_address(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    address_columns = [
        column
        for column in [
            "Address",
            "Country Tertiary Subdivision",
            "Country Secondary Subdivision",
            "Country",
        ]
        if column in result.columns
    ]

    if not address_columns:
        raise KeyError("No address columns were found to build 'Full Address'.")

    def join_parts(row: pd.Series) -> str:
        parts = [str(row[column]).strip() for column in address_columns if pd.notna(row[column]) and str(row[column]).strip()]
        return ", ".join(parts)

    result["Full Address"] = result.apply(join_parts, axis=1)
    return result


def geocode_addresses(
    df: pd.DataFrame,
    user_agent: str = "lucas_geocoder",
    timeout: int = 10,
    min_delay_seconds: float = 1.0,
) -> pd.DataFrame:
    result = df.copy()
    if {"lat", "lon"}.issubset(result.columns) and result["lat"].notna().all() and result["lon"].notna().all():
        return result

    geolocator = Nominatim(user_agent=user_agent, timeout=timeout)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=min_delay_seconds)
    result["location"] = result["Full Address"].apply(geocode)
    result["lat"] = result["location"].apply(lambda value: value.latitude if value else None)
    result["lon"] = result["location"].apply(lambda value: value.longitude if value else None)
    return result


def create_client_geodataframe(df: pd.DataFrame, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    if not {"lat", "lon"}.issubset(df.columns):
        raise KeyError("Expected 'lat' and 'lon' columns before creating a GeoDataFrame.")

    valid_mask = df["lat"].notna() & df["lon"].notna()
    if not valid_mask.all():
        dropped = int((~valid_mask).sum())
        warnings.warn(f"Skipping {dropped} client location(s) without geocoded coordinates.", RuntimeWarning)

    cleaned = df.loc[valid_mask].copy()
    geometry = [Point(xy) for xy in zip(cleaned["lon"], cleaned["lat"])]
    return gpd.GeoDataFrame(cleaned, geometry=geometry, crs=crs)


def project_to_meters(gdf: gpd.GeoDataFrame, epsg: int = 3857) -> gpd.GeoDataFrame:
    return gdf.to_crs(epsg=epsg)


def create_buffers(
    df: pd.DataFrame,
    buffer_sizes_m: Iterable[int] = (5000, 10000),
    projected_epsg: int = 3857,
    return_projected: bool = False,
):
    gdf = create_client_geodataframe(df)
    gdf_proj = project_to_meters(gdf, epsg=projected_epsg)

    buffer_sizes = list(buffer_sizes_m)
    for buffer_size in buffer_sizes:
        gdf_proj[f"geometry_{int(buffer_size / 1000)}km"] = gdf_proj.geometry.buffer(buffer_size)

    gdf_buffers = gdf_proj.to_crs(epsg=4326)
    if return_projected:
        return gdf_proj, gdf_buffers
    return gdf_buffers


def create_buffer_geometries(
    gdf: gpd.GeoDataFrame,
    buffer_sizes_m: Iterable[int] = (5000, 10000),
    projected_epsg: int = 3857,
) -> gpd.GeoDataFrame:
    gdf_proj = project_to_meters(gdf, epsg=projected_epsg)
    for buffer_size in buffer_sizes_m:
        gdf_proj[f"geometry_{int(buffer_size / 1000)}km"] = gdf_proj.geometry.buffer(buffer_size)
    return gdf_proj
