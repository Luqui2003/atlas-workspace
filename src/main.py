from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

try:
    from .analysis import (
        build_osm_category_table,
        compute_cannibalization,
        compute_location_scores,
        compute_white_spots,
        export_powerbi_tables,
        filter_points_in_client_buffers,
        filter_points_in_partidos,
    )
    from .data_loading import load_locations, load_osm_relevant_points, load_partidos
    from .processing import add_full_address, create_buffers, create_client_geodataframe, geocode_addresses
    from .visualization import (
        map_amenities,
        map_cannibalization,
        map_location_scores,
        map_partidos_points,
        map_points_in_buffers,
        map_white_spots,
        map_with_buffers,
    )
except ImportError:  # pragma: no cover - supports direct script execution
    from analysis import (
        build_osm_category_table,
        compute_cannibalization,
        compute_location_scores,
        compute_white_spots,
        export_powerbi_tables,
        filter_points_in_client_buffers,
        filter_points_in_partidos,
    )
    from data_loading import load_locations, load_osm_relevant_points, load_partidos
    from processing import add_full_address, create_buffers, create_client_geodataframe, geocode_addresses
    from visualization import (
        map_amenities,
        map_cannibalization,
        map_location_scores,
        map_partidos_points,
        map_points_in_buffers,
        map_white_spots,
        map_with_buffers,
    )


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_input_path(root: Path, relative_or_absolute: str) -> Path:
    candidate = Path(relative_or_absolute)
    if candidate.is_absolute():
        return candidate
    return (root / candidate).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full geospatial analysis pipeline.")
    parser.add_argument("--excel-path", default="data/Location Example 1.xlsx", help="Input Excel file with client locations.")
    parser.add_argument("--pbf-path", default="data/osmbsas/argentina-260316.osm.pbf", help="OSM PBF file with amenities.")
    parser.add_argument("--partidos-path", default="data/partidoslimits/shp/partidos.shp", help="Partidos shapefile path.")
    parser.add_argument("--output-dir", default="outputs", help="Directory where derived outputs will be written.")
    args = parser.parse_args()

    root = project_root()
    output_dir = resolve_input_path(root, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    excel_path = resolve_input_path(root, args.excel_path)
    pbf_path = resolve_input_path(root, args.pbf_path)
    partidos_path = resolve_input_path(root, args.partidos_path)

    # Client locations
    locations_df = load_locations(excel_path)
    locations_df = add_full_address(locations_df)
    locations_df = geocode_addresses(locations_df)
    client_gdf = create_client_geodataframe(locations_df)
    client_buffers_proj, client_buffers_ll = create_buffers(locations_df, return_projected=True)

    map_with_buffers(client_buffers_ll, str(output_dir / "mapaconbuffers.html"))

    # OSM relevant points
    points_gdf = load_osm_relevant_points(pbf_path)
    map_amenities(points_gdf, str(output_dir / "argentina_amenities_full.html"))

    # Client buffers analysis
    client_buffers_10km_proj = gpd.GeoDataFrame(
        client_buffers_proj[["Full Address", "geometry_10km"]].copy(),
        geometry="geometry_10km",
        crs=client_buffers_proj.crs,
    )
    points_in_client_buffers_proj = filter_points_in_client_buffers(points_gdf, client_buffers_10km_proj)
    points_in_client_buffers = points_in_client_buffers_proj.to_crs(epsg=4326)
    map_points_in_buffers(client_buffers_ll, points_in_client_buffers, str(output_dir / "locations_inside_client_buffers.html"))
    points_in_client_buffers.to_csv(output_dir / "points_inside_client_buffers.csv", index=False)

    # Partidos and AMBA Norte analysis
    partidos_gdf = load_partidos(partidos_path)
    partidos_to_check = [
        "General San Martín", "Malvinas Argentinas", "San Fernando",
        "San Isidro", "San Miguel", "Tigre", "Tres de Febrero",
        "Vicente López", "Escobar", "Pilar", "José C. Paz",
    ]
    partidos_ambanorte = partidos_gdf[partidos_gdf["nam"].isin(partidos_to_check)].copy()
    points_ambanorte = filter_points_in_partidos(points_gdf, partidos_ambanorte)
    points_ambanorte_ll = points_ambanorte.to_crs(epsg=4326)
    map_partidos_points(partidos_ambanorte, points_ambanorte_ll, str(output_dir / "argentina_relevant_locations_amba_norte.html"))

    # OSM category breakdown inside client buffers
    category_counts, category_values = build_osm_category_table(points_in_client_buffers)
    category_counts.to_csv(output_dir / "osm_category_counts.csv")
    category_values.to_csv(output_dir / "osm_category_values.csv", index=False)

    # White spot analysis
    white_spots = compute_white_spots(partidos_ambanorte, client_gdf, points_ambanorte)
    top_white_spots_ll = white_spots["top_white_spots_ll"]
    top_white_spots_ll.to_csv(output_dir / "amba_norte_white_spots_top25.csv", index=False)
    map_white_spots(
        partidos_ambanorte,
        white_spots["clients_ambanorte_3857"].to_crs(epsg=4326),
        white_spots["osm_ambanorte_3857"].to_crs(epsg=4326),
        top_white_spots_ll,
        str(output_dir / "amba_norte_white_spots.html"),
    )

    # Client proximity score analysis
    scores_df = compute_location_scores(client_gdf, points_gdf)
    scores_df.to_csv(output_dir / "client_location_osm_proximity_scores.csv", index=False)

    clients_ll = client_buffers_proj.to_crs(epsg=4326)[["Full Address", "geometry"]].copy()
    clients_ll["lat"] = clients_ll.geometry.y
    clients_ll["lon"] = clients_ll.geometry.x
    client_buffers_5km_proj = gpd.GeoDataFrame(
        client_buffers_proj[["Full Address", "geometry_5km"]].copy(),
        geometry="geometry_5km",
        crs=client_buffers_proj.crs,
    )
    points_in_5km_proj = filter_points_in_client_buffers(points_gdf, client_buffers_5km_proj)
    map_location_scores(
        clients_ll,
        points_in_5km_proj.to_crs(epsg=4326),
        points_in_client_buffers.to_crs(epsg=4326),
        str(output_dir / "client_location_osm_proximity_scores_map.html"),
    )

    # Cannibalization analysis
    cannibalization = compute_cannibalization(client_gdf)
    cannibalization["cannibalization_df"].to_csv(output_dir / "client_cannibalization_pairs.csv", index=False)
    map_cannibalization(
        cannibalization["clients_ll"],
        cannibalization["overlap5_geoms"],
        cannibalization["overlap10_geoms"],
        cannibalization["coverage_10km"],
        str(output_dir / "client_cannibalization_map.html"),
    )

    # Power BI export
    export_dir = output_dir / "powerbi_exports"
    fact_df = export_powerbi_tables(
        export_dir,
        clients_gdf=client_gdf,
        points_gdf=points_gdf,
        partidos_gdf=partidos_ambanorte,
        white_spots_gdf=top_white_spots_ll,
        points_ambanorte_gdf=points_ambanorte_ll,
        cannibalization_result=cannibalization,
    )

    print(f"Saved Power BI export to {export_dir / 'geospatial_analysis_flat.csv'}")
    print(f"Exported rows: {len(fact_df):,}")


if __name__ == "__main__":
    main()
