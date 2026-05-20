from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box
from shapely.ops import transform as _shapely_transform
from pyproj import Transformer


def _to_crs(gdf: gpd.GeoDataFrame, epsg: int) -> gpd.GeoDataFrame:
    if gdf.crs and gdf.crs.to_epsg() == epsg:
        return gdf.copy()
    return gdf.to_crs(epsg=epsg)


def filter_points_within_geometry(
    points_gdf: gpd.GeoDataFrame,
    geometry,
    target_epsg: int = 3857,
) -> gpd.GeoDataFrame:
    points_proj = _to_crs(points_gdf, target_epsg)
    filtered = points_proj[points_proj.geometry.within(geometry)].copy()
    return filtered


def filter_points_in_client_buffers(
    points_gdf: gpd.GeoDataFrame,
    client_buffers_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    buffer_union = client_buffers_gdf.geometry.union_all()
    return filter_points_within_geometry(points_gdf, buffer_union, target_epsg=client_buffers_gdf.crs.to_epsg())


def filter_points_in_partidos(
    points_gdf: gpd.GeoDataFrame,
    partidos_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    points = points_gdf.copy()
    partidos = partidos_gdf.copy()
    if points.crs != partidos.crs:
        points = points.to_crs(partidos.crs)
    joined = gpd.sjoin(points, partidos[["nam", "geometry"]], how="inner", predicate="intersects")
    return joined.drop(columns=[column for column in ["index_right"] if column in joined.columns])


def build_osm_category_table(points_gdf: gpd.GeoDataFrame) -> tuple[pd.Series, pd.DataFrame]:
    category_priority = [
        "amenity", "shop", "tourism", "leisure", "highway",
        "public_transport", "railway", "aeroway", "building",
        "landuse", "office", "craft", "industrial", "healthcare", "education",
    ]

    def pick_category(tags):
        for category in category_priority:
            if category in tags:
                return category
        return "other_tagged"

    buffer_points = points_gdf.copy()
    buffer_points["osm_category"] = buffer_points["tags"].apply(pick_category)
    counts = buffer_points["osm_category"].value_counts()

    from collections import Counter

    category_value_counter = Counter()
    for _, row in buffer_points.iterrows():
        tags = row["tags"]
        category = row["osm_category"]
        if category != "other_tagged":
            value = tags.get(category, "(missing)")
            category_value_counter[(category, value)] += 1

    category_values = pd.DataFrame(
        [
            {"category": key[0], "value": key[1], "count": value}
            for key, value in category_value_counter.items()
        ]
    ).sort_values("count", ascending=False).reset_index(drop=True)

    return counts, category_values


def compute_white_spots(
    partidos_ambanorte: gpd.GeoDataFrame,
    clients_gdf: gpd.GeoDataFrame,
    points_gdf: gpd.GeoDataFrame,
    grid_size_m: int = 1000,
    service_radius_m: int = 5000,
    demand_radius_m: int = 1500,
    w_demand: float = 0.65,
    w_gap: float = 0.35,
    top_n: int = 25,
) -> dict:
    amba_norte_3857 = _to_crs(partidos_ambanorte, 3857)
    amba_union = amba_norte_3857.geometry.union_all()

    osm_ambanorte_3857 = _to_crs(points_gdf, 3857)
    clients_3857 = _to_crs(clients_gdf, 3857)
    clients_ambanorte_3857 = gpd.sjoin(
        clients_3857,
        amba_norte_3857[["nam", "geometry"]],
        how="inner",
        predicate="intersects",
    )
    if "index_right" in clients_ambanorte_3857.columns:
        clients_ambanorte_3857 = clients_ambanorte_3857.drop(columns=["index_right"])

    if clients_ambanorte_3857.empty:
        raise ValueError("No client locations found inside AMBA Norte. Check input client addresses.")

    minx, miny, maxx, maxy = amba_union.bounds
    x_coords = np.arange(minx, maxx, grid_size_m)
    y_coords = np.arange(miny, maxy, grid_size_m)
    cells = [box(x, y, x + grid_size_m, y + grid_size_m) for x in x_coords for y in y_coords]

    grid = gpd.GeoDataFrame({"geometry": cells}, crs="EPSG:3857")
    grid = gpd.overlay(grid, gpd.GeoDataFrame(geometry=[amba_union], crs="EPSG:3857"), how="intersection")
    grid = grid[grid.area > 0].copy()
    grid["cell_id"] = range(1, len(grid) + 1)
    grid["centroid"] = grid.geometry.centroid

    client_union = clients_ambanorte_3857.geometry.union_all()
    osm_sindex = osm_ambanorte_3857.sindex
    grid["dist_to_nearest_client_m"] = grid["centroid"].distance(client_union)

    osm_density = []
    for centroid in grid["centroid"]:
        search_area = centroid.buffer(demand_radius_m)
        candidate_idx = list(osm_sindex.intersection(search_area.bounds))
        if not candidate_idx:
            osm_density.append(0)
            continue
        candidates = osm_ambanorte_3857.iloc[candidate_idx]
        osm_density.append(int(candidates.geometry.within(search_area).sum()))
    grid["osm_points_nearby"] = osm_density

    if grid["osm_points_nearby"].max() == grid["osm_points_nearby"].min():
        grid["osm_norm"] = 0.0
    else:
        grid["osm_norm"] = (
            (grid["osm_points_nearby"] - grid["osm_points_nearby"].min())
            / (grid["osm_points_nearby"].max() - grid["osm_points_nearby"].min())
        )

    if grid["dist_to_nearest_client_m"].max() == grid["dist_to_nearest_client_m"].min():
        grid["gap_norm"] = 0.0
    else:
        grid["gap_norm"] = (
            (grid["dist_to_nearest_client_m"] - grid["dist_to_nearest_client_m"].min())
            / (grid["dist_to_nearest_client_m"].max() - grid["dist_to_nearest_client_m"].min())
        )

    white_spot_candidates = grid[grid["dist_to_nearest_client_m"] > service_radius_m].copy()
    white_spot_candidates["white_spot_score"] = (
        w_demand * white_spot_candidates["osm_norm"]
        + w_gap * white_spot_candidates["gap_norm"]
    )
    white_spot_candidates = white_spot_candidates.sort_values("white_spot_score", ascending=False).reset_index(drop=True)

    top_white_spots = white_spot_candidates.head(top_n).copy()
    top_white_spots_ll = top_white_spots.copy()
    top_white_spots_ll["geometry"] = top_white_spots_ll["centroid"]
    top_white_spots_ll = top_white_spots_ll.set_geometry("geometry").to_crs(epsg=4326)
    top_white_spots_ll["lat"] = top_white_spots_ll.geometry.y
    top_white_spots_ll["lon"] = top_white_spots_ll.geometry.x

    center_point = gpd.GeoSeries([amba_union.centroid], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]

    return {
        "grid": grid,
        "white_spot_candidates": white_spot_candidates,
        "top_white_spots": top_white_spots,
        "top_white_spots_ll": top_white_spots_ll,
        "clients_ambanorte_3857": clients_ambanorte_3857,
        "osm_ambanorte_3857": osm_ambanorte_3857,
        "center_point": center_point,
    }


def compute_location_scores(
    clients_gdf: gpd.GeoDataFrame,
    points_gdf: gpd.GeoDataFrame,
) -> pd.DataFrame:
    clients_3857 = _to_crs(clients_gdf[["Full Address", "geometry"]].copy(), 3857)
    osm_3857 = _to_crs(points_gdf[["id", "geometry"]].copy(), 3857)
    osm_sindex = osm_3857.sindex

    rows = []
    for idx, row in clients_3857.iterrows():
        client_point = row.geometry
        buffer_10km = client_point.buffer(10000)
        candidate_idx = list(osm_sindex.intersection(buffer_10km.bounds))

        if candidate_idx:
            candidates = osm_3857.iloc[candidate_idx]
            dists_m = candidates.geometry.distance(client_point)
            count_5km = int((dists_m <= 5000).sum())
            count_10km = int((dists_m <= 10000).sum())
        else:
            count_5km = 0
            count_10km = 0

        ring_5_10km = count_10km - count_5km
        raw_score = 0.7 * count_5km + 0.3 * ring_5_10km

        rows.append({
            "location_idx": idx,
            "Full Address": row["Full Address"],
            "osm_count_5km": count_5km,
            "osm_count_10km": count_10km,
            "osm_count_ring_5_10km": ring_5_10km,
            "raw_score": raw_score,
        })

    scores_df = pd.DataFrame(rows)
    if scores_df["raw_score"].max() == scores_df["raw_score"].min():
        scores_df["location_score"] = 0.0
    else:
        scores_df["location_score"] = (
            (scores_df["raw_score"] - scores_df["raw_score"].min())
            / (scores_df["raw_score"].max() - scores_df["raw_score"].min())
        ) * 100

    clients_ll = clients_gdf[["Full Address", "geometry"]].copy().to_crs(epsg=4326)
    clients_ll["lat"] = clients_ll.geometry.y
    clients_ll["lon"] = clients_ll.geometry.x

    scores_df = scores_df.merge(
        clients_ll[["Full Address", "lat", "lon"]],
        on="Full Address",
        how="left",
    )

    return scores_df.sort_values("location_score", ascending=False).reset_index(drop=True)


def compute_cannibalization(clients_gdf: gpd.GeoDataFrame) -> dict:
    clients_src = clients_gdf[["Full Address", "geometry"]].copy()
    clients_src = clients_src[clients_src.geometry.notna() & ~clients_src.geometry.is_empty].copy().reset_index(drop=True)

    if len(clients_src) < 2:
        raise ValueError("At least 2 client locations are required for cannibalization analysis.")

    clients_3857 = clients_src.to_crs(epsg=3857)
    clients_3857["client_id"] = clients_3857.index + 1
    clients_3857["buffer_5km"] = clients_3857.geometry.buffer(5000)
    clients_3857["buffer_10km"] = clients_3857.geometry.buffer(10000)

    circle_area_5km_km2 = np.pi * (5 ** 2)
    circle_area_10km_km2 = np.pi * (10 ** 2)

    pair_rows = []
    overlap5_geoms = []
    overlap10_geoms = []

    for i, j in combinations(clients_3857.index, 2):
        a = clients_3857.loc[i]
        b = clients_3857.loc[j]
        distance_m = float(a.geometry.distance(b.geometry))

        ov5 = a["buffer_5km"].intersection(b["buffer_5km"])
        ov10 = a["buffer_10km"].intersection(b["buffer_10km"])

        ov5_area_km2 = float(ov5.area / 1_000_000) if not ov5.is_empty else 0.0
        ov10_area_km2 = float(ov10.area / 1_000_000) if not ov10.is_empty else 0.0
        ov5_pct_of_circle = (ov5_area_km2 / circle_area_5km_km2) * 100
        ov10_pct_of_circle = (ov10_area_km2 / circle_area_10km_km2) * 100
        cannibalization_index = min(100.0, (0.65 * ov5_pct_of_circle) + (0.35 * ov10_pct_of_circle))

        pair_rows.append({
            "client_id_a": int(a["client_id"]),
            "client_a": a["Full Address"],
            "client_id_b": int(b["client_id"]),
            "client_b": b["Full Address"],
            "distance_m": round(distance_m, 1),
            "distance_km": round(distance_m / 1000, 3),
            "overlap_5km_area_km2": round(ov5_area_km2, 4),
            "overlap_10km_area_km2": round(ov10_area_km2, 4),
            "overlap_5km_pct_of_circle": round(ov5_pct_of_circle, 2),
            "overlap_10km_pct_of_circle": round(ov10_pct_of_circle, 2),
            "cannibalization_index_0_100": round(cannibalization_index, 2),
            "cannibalization_5km": ov5_area_km2 > 0,
            "cannibalization_10km": ov10_area_km2 > 0,
        })

        if not ov5.is_empty:
            overlap5_geoms.append(ov5)
        if not ov10.is_empty:
            overlap10_geoms.append(ov10)

    cannibalization_df = pd.DataFrame(pair_rows).sort_values(
        "cannibalization_index_0_100", ascending=False
    ).reset_index(drop=True)

    clients_ll = clients_3857.to_crs(epsg=4326)
    coverage_10km = clients_3857["buffer_10km"].union_all()

    return {
        "cannibalization_df": cannibalization_df,
        "clients_3857": clients_3857,
        "clients_ll": clients_ll,
        "coverage_10km": coverage_10km,
        "overlap5_geoms": overlap5_geoms,
        "overlap10_geoms": overlap10_geoms,
    }


def _point_like_ll(value, crs):
    if value is None or value.is_empty:
        return (None, None)
    series = gpd.GeoSeries([value], crs=crs).to_crs(epsg=4326)
    geom = series.iloc[0]
    anchor = geom if geom.geom_type == "Point" else geom.centroid
    return (float(anchor.y), float(anchor.x))


def export_powerbi_tables(
    output_dir: str | Path,
    clients_gdf: gpd.GeoDataFrame | None = None,
    points_gdf: gpd.GeoDataFrame | None = None,
    partidos_gdf: gpd.GeoDataFrame | None = None,
    white_spots_gdf: gpd.GeoDataFrame | None = None,
    points_ambanorte_gdf: gpd.GeoDataFrame | None = None,
    cannibalization_result: dict | None = None,
) -> pd.DataFrame:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fact_rows: list[dict] = []

    # compute location scores mapping if points are available
    location_score_map = {}
    try:
        if clients_gdf is not None and points_gdf is not None:
            scores_df = compute_location_scores(clients_gdf, points_gdf)
            if "Full Address" in scores_df.columns and "location_score" in scores_df.columns:
                location_score_map = scores_df.set_index("Full Address")["location_score"].to_dict()
    except Exception:
        # do not fail exports if scoring fails
        location_score_map = {}

    if clients_gdf is not None:
        clients_src = clients_gdf[["Full Address", "geometry"]].copy()
        clients_src = clients_src[clients_src.geometry.notna() & ~clients_src.geometry.is_empty].copy().reset_index(drop=True)
        clients_3857 = clients_src.to_crs(epsg=3857)
        clients_ll = clients_src.to_crs(epsg=4326)

        for idx, row in clients_src.iterrows():
            ll_point = clients_ll.iloc[idx].geometry
            fact_rows.append({
                "source_table": "dim_client_locations",
                "analysis_name": "client_location",
                "feature_type": "point",
                "feature_id": idx + 1,
                "feature_name": row["Full Address"],
                "parent_id": None,
                "lat": float(ll_point.y),
                "lon": float(ll_point.x),
                "geometry_wkt": clients_ll.iloc[idx].geometry.wkt,
                "location_score": location_score_map.get(row["Full Address"], None),
                "area_km2": 0.0,
                "perimeter_km": 0.0,
                "metric_1": None,
                "metric_2": None,
                "metric_3": None,
            })

        for idx, row in clients_3857.iterrows():
            buffer_5km = row.geometry.buffer(5000)
            buffer_10km = row.geometry.buffer(10000)
            ll_point = clients_ll.iloc[idx].geometry
            fact_rows.append({
                "source_table": "dim_client_buffers",
                "analysis_name": "client_buffer_5km",
                "feature_type": "polygon",
                "feature_id": f"{idx + 1}_5km",
                "feature_name": clients_src.iloc[idx]["Full Address"],
                "parent_id": idx + 1,
                "lat": float(ll_point.y),
                "lon": float(ll_point.x),
                # reproject buffer geometry to WGS84 explicitly and export WKT
                "geometry_wkt": _shapely_transform(
                    Transformer.from_crs(clients_3857.crs, "EPSG:4326", always_xy=True).transform,
                    buffer_5km,
                ).wkt,
                "area_km2": float(buffer_5km.area / 1_000_000),
                "perimeter_km": float(buffer_5km.length / 1_000),
                "metric_1": 5000,
                "metric_2": None,
                "metric_3": None,
            })
            fact_rows.append({
                "source_table": "dim_client_buffers",
                "analysis_name": "client_buffer_10km",
                "feature_type": "polygon",
                "feature_id": f"{idx + 1}_10km",
                "feature_name": clients_src.iloc[idx]["Full Address"],
                "parent_id": idx + 1,
                "lat": float(ll_point.y),
                "lon": float(ll_point.x),
                # reproject buffer geometry to WGS84 explicitly and export WKT
                "geometry_wkt": _shapely_transform(
                    Transformer.from_crs(clients_3857.crs, "EPSG:4326", always_xy=True).transform,
                    buffer_10km,
                ).wkt,
                "area_km2": float(buffer_10km.area / 1_000_000),
                "perimeter_km": float(buffer_10km.length / 1_000),
                "metric_1": 10000,
                "metric_2": None,
                "metric_3": None,
            })

    if points_gdf is not None:
        points_src = points_gdf[points_gdf.geometry.notna() & ~points_gdf.geometry.is_empty].copy().reset_index(drop=True)
        points_ll = points_src.to_crs(epsg=4326)
        for idx, row in points_src.iterrows():
            lat, lon = _point_like_ll(row.geometry, points_src.crs)
            fact_rows.append({
                "source_table": "dim_osm_points",
                "analysis_name": "relevant_osm_point",
                "feature_type": row.geometry.geom_type.lower(),
                "feature_id": int(row.get("id", idx + 1)),
                "feature_name": row.get("name", "Unnamed OSM point"),
                "parent_id": None,
                "lat": lat,
                "lon": lon,
                "geometry_wkt": points_ll.iloc[idx].geometry.wkt,
                "area_km2": float(row.geometry.area / 1_000_000) if row.geometry.geom_type != "Point" else 0.0,
                "perimeter_km": float(row.geometry.length / 1_000) if row.geometry.geom_type != "Point" else 0.0,
                "metric_1": row.get("element"),
                "metric_2": row.get("amenity", row.get("shop")),
                "metric_3": row.get("tourism", row.get("leisure")),
            })

    if points_ambanorte_gdf is not None:
        points_ambanorte_src = points_ambanorte_gdf[points_ambanorte_gdf.geometry.notna() & ~points_ambanorte_gdf.geometry.is_empty].copy().reset_index(drop=True)
        points_ambanorte_ll = points_ambanorte_src.to_crs(epsg=4326)
        for idx, row in points_ambanorte_src.iterrows():
            lat, lon = _point_like_ll(row.geometry, points_ambanorte_src.crs)
            fact_rows.append({
                "source_table": "fact_osm_points_amba_norte",
                "analysis_name": "osm_point_in_amba_norte",
                "feature_type": row.geometry.geom_type.lower(),
                "feature_id": int(row.get("id", idx + 1)),
                "feature_name": row.get("name", "Unnamed OSM point"),
                "parent_id": None,
                "lat": lat,
                "lon": lon,
                "geometry_wkt": points_ambanorte_ll.iloc[idx].geometry.wkt,
                "area_km2": float(row.geometry.area / 1_000_000) if row.geometry.geom_type != "Point" else 0.0,
                "perimeter_km": float(row.geometry.length / 1_000) if row.geometry.geom_type != "Point" else 0.0,
                "metric_1": row.get("nam"),
                "metric_2": row.get("tags"),
                "metric_3": None,
            })

    if partidos_gdf is not None:
        partidos_src = partidos_gdf[partidos_gdf.geometry.notna() & ~partidos_gdf.geometry.is_empty].copy().reset_index(drop=True)
        partidos_ll = partidos_src.to_crs(epsg=4326)
        for idx, row in partidos_src.iterrows():
            ll_centroid = partidos_ll.iloc[idx].geometry.centroid
            fact_rows.append({
                "source_table": "dim_partidos",
                "analysis_name": "partidos_boundary",
                "feature_type": "polygon",
                "feature_id": idx + 1,
                "feature_name": row.get("nam"),
                "parent_id": None,
                "lat": float(ll_centroid.y),
                "lon": float(ll_centroid.x),
                "geometry_wkt": partidos_ll.iloc[idx].geometry.wkt,
                "area_km2": float(row.geometry.area / 1_000_000),
                "perimeter_km": float(row.geometry.length / 1_000),
                "metric_1": row.get("sag"),
                "metric_2": None,
                "metric_3": None,
            })

    if white_spots_gdf is not None:
        white_spots_src = white_spots_gdf.copy()
        if not isinstance(white_spots_src, gpd.GeoDataFrame):
            raise TypeError("white_spots_gdf must be a GeoDataFrame.")
        # ensure white spot geometries are in WGS84 for export
        white_spots_src = white_spots_src.to_crs(epsg=4326)
        for idx, row in white_spots_src.reset_index(drop=True).iterrows():
            fact_rows.append({
                "source_table": "dim_white_spot_cells",
                "analysis_name": "white_spot_candidate",
                "feature_type": "point",
                "feature_id": int(row.get("cell_id", idx + 1)),
                "feature_name": f"White spot {idx + 1}",
                "parent_id": None,
                "lat": float(row.geometry.y),
                "lon": float(row.geometry.x),
                "geometry_wkt": row.geometry.wkt,
                "area_km2": 0.0,
                "perimeter_km": 0.0,
                "metric_1": float(row.get("white_spot_score", 0.0)),
                "metric_2": float(row.get("osm_points_nearby", 0.0)),
                "metric_3": float(row.get("dist_to_nearest_client_m", 0.0)),
            })

    if cannibalization_result is not None:
        clients_3857 = cannibalization_result["clients_3857"]
        clients_ll = cannibalization_result["clients_ll"]
        overlap5_geoms = cannibalization_result["overlap5_geoms"]
        overlap10_geoms = cannibalization_result["overlap10_geoms"]
    elif clients_gdf is not None and len(clients_gdf) >= 2:
        cannibalization_result = compute_cannibalization(clients_gdf)
        clients_3857 = cannibalization_result["clients_3857"]
        clients_ll = cannibalization_result["clients_ll"]
        overlap5_geoms = cannibalization_result["overlap5_geoms"]
        overlap10_geoms = cannibalization_result["overlap10_geoms"]
    else:
        overlap5_geoms = []
        overlap10_geoms = []
        clients_3857 = None
        clients_ll = None

    if clients_3857 is not None:
        for i, j in combinations(clients_3857.index, 2):
            a = clients_3857.loc[i]
            b = clients_3857.loc[j]
            ov5 = a["buffer_5km"].intersection(b["buffer_5km"])
            ov10 = a["buffer_10km"].intersection(b["buffer_10km"])
            if not ov5.is_empty:
                lat, lon = _point_like_ll(ov5.centroid, clients_3857.crs)
                fact_rows.append({
                    "source_table": "dim_cannibalization_zones",
                    "analysis_name": "cannibalization_5km_overlap",
                    "feature_type": "polygon",
                    "feature_id": f"{int(a['client_id'])}_{int(b['client_id'])}_5km",
                    "feature_name": f"Client {int(a['client_id'])} x Client {int(b['client_id'])}",
                    "parent_id": None,
                    "lat": lat,
                    "lon": lon,
                    # convert overlap geometry to WGS84 for WKT export
                    "geometry_wkt": _shapely_transform(
                        Transformer.from_crs(clients_3857.crs, "EPSG:4326", always_xy=True).transform,
                        ov5,
                    ).wkt,
                    "area_km2": float(ov5.area / 1_000_000),
                    "perimeter_km": float(ov5.length / 1_000),
                    "metric_1": 5000,
                    "metric_2": int(a["client_id"]),
                    "metric_3": int(b["client_id"]),
                })
            if not ov10.is_empty:
                lat, lon = _point_like_ll(ov10.centroid, clients_3857.crs)
                fact_rows.append({
                    "source_table": "dim_cannibalization_zones",
                    "analysis_name": "cannibalization_10km_overlap",
                    "feature_type": "polygon",
                    "feature_id": f"{int(a['client_id'])}_{int(b['client_id'])}_10km",
                    "feature_name": f"Client {int(a['client_id'])} x Client {int(b['client_id'])}",
                    "parent_id": None,
                    "lat": lat,
                    "lon": lon,
                    # convert overlap geometry to WGS84 for WKT export
                    "geometry_wkt": _shapely_transform(
                        Transformer.from_crs(clients_3857.crs, "EPSG:4326", always_xy=True).transform,
                        ov10,
                    ).wkt,
                    "area_km2": float(ov10.area / 1_000_000),
                    "perimeter_km": float(ov10.length / 1_000),
                    "metric_1": 10000,
                    "metric_2": int(a["client_id"]),
                    "metric_3": int(b["client_id"]),
                })

    fact_df = pd.DataFrame(fact_rows)
    if fact_df.empty:
        raise ValueError("No exportable geospatial tables were found.")

    flat_out = output_dir / "geospatial_analysis_flat.csv"
    fact_df.to_csv(flat_out, index=False)

    table_names = [
        "dim_client_locations",
        "dim_client_buffers",
        "dim_osm_points",
        "fact_osm_points_amba_norte",
        "dim_partidos",
        "dim_white_spot_cells",
        "dim_cannibalization_zones",
    ]
    for table_name in table_names:
        table_out = output_dir / f"{table_name}.csv"
        fact_df[fact_df["source_table"] == table_name].to_csv(table_out, index=False)

    return fact_df
