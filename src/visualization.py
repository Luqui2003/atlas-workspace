from __future__ import annotations

from typing import Iterable

import folium
import geopandas as gpd


def _map_center_from_points(gdf: gpd.GeoDataFrame) -> list[float]:
    return [float(gdf.geometry.y.mean()), float(gdf.geometry.x.mean())]


def map_with_buffers(gdf_buffers: gpd.GeoDataFrame, output_path: str) -> None:
    center = [float(gdf_buffers["lat"].mean()), float(gdf_buffers["lon"].mean())]
    m = folium.Map(location=center, zoom_start=5, tiles="CartoDB positron")

    for _, row in gdf_buffers.iterrows():
        lat = float(row["lat"])
        lon = float(row["lon"])
        folium.Marker(location=[lat, lon], popup=row["Full Address"], tooltip=row["Full Address"]).add_to(m)
        folium.Circle(location=[lat, lon], radius=5000, color="blue", fill=True, fill_opacity=0.2).add_to(m)
        folium.Circle(location=[lat, lon], radius=10000, color="red", fill=True, fill_opacity=0.2).add_to(m)

    m.save(output_path)


def map_amenities(points, output_path: str) -> None:
    m = folium.Map(location=[-34.6, -58.4], zoom_start=5, tiles="CartoDB positron")

    if isinstance(points, gpd.GeoDataFrame):
        source = points.copy()
        if source.empty:
            m.save(output_path)
            return
        for _, row in source.iterrows():
            geom = row.geometry
            if geom.geom_type == "Point":
                lat, lon = float(geom.y), float(geom.x)
            else:
                centroid = geom.centroid
                lat, lon = float(centroid.y), float(centroid.x)
            folium.CircleMarker(location=[lat, lon], radius=1, fill=True, color="#d1495b", fill_color="#d1495b", fill_opacity=0.8, weight=0).add_to(m)
    else:
        for lat, lon in points:
            folium.CircleMarker(location=[lat, lon], radius=1, fill=True, color="#d1495b", fill_color="#d1495b", fill_opacity=0.8, weight=0).add_to(m)

    m.save(output_path)


def map_points_in_buffers(
    gdf_buffers: gpd.GeoDataFrame,
    points_in_client_buffers: gpd.GeoDataFrame,
    output_path: str,
) -> None:
    center = [float(gdf_buffers["lat"].mean()), float(gdf_buffers["lon"].mean())]
    m = folium.Map(location=center, zoom_start=9, tiles="CartoDB positron")

    for _, row in gdf_buffers.iterrows():
        lat = float(row["lat"])
        lon = float(row["lon"])
        folium.Marker(
            location=[lat, lon],
            popup=row["Full Address"],
            tooltip=row["Full Address"],
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(m)
        folium.Circle(location=[lat, lon], radius=5000, color="blue", fill=True, fill_opacity=0.08, weight=1).add_to(m)
        folium.Circle(location=[lat, lon], radius=10000, color="red", fill=True, fill_opacity=0.04, weight=1).add_to(m)

    for _, row in points_in_client_buffers.iterrows():
        geom = row.geometry
        folium.CircleMarker(
            location=[float(geom.y), float(geom.x)],
            radius=1,
            fill=True,
            color="#d1495b",
            fill_color="#d1495b",
            fill_opacity=0.8,
            weight=0,
        ).add_to(m)

    m.save(output_path)


def map_partidos_points(
    partidos_ambanorte: gpd.GeoDataFrame,
    points_ambanorte: gpd.GeoDataFrame,
    output_path: str,
) -> None:
    center = [float(points_ambanorte.geometry.y.mean()), float(points_ambanorte.geometry.x.mean())]
    m = folium.Map(location=center, zoom_start=10, tiles="CartoDB positron")

    folium.GeoJson(
        partidos_ambanorte,
        name="partidos_ambanorte",
        style_function=lambda _: {
            "fillColor": "#1f77b4",
            "color": "#111111",
            "weight": 2,
            "fillOpacity": 0.15,
        },
    ).add_to(m)

    for _, row in points_ambanorte.iterrows():
        geom = row.geometry
        folium.CircleMarker(
            location=[float(geom.y), float(geom.x)],
            radius=1,
            fill=True,
            color="#d1495b",
            fill_color="#d1495b",
            fill_opacity=0.8,
            weight=0,
        ).add_to(m)

    folium.LayerControl().add_to(m)
    m.save(output_path)


def map_white_spots(
    partidos_ambanorte: gpd.GeoDataFrame,
    clients_ambanorte_ll: gpd.GeoDataFrame,
    osm_ambanorte_ll: gpd.GeoDataFrame,
    top_white_spots_ll: gpd.GeoDataFrame,
    output_path: str,
) -> None:
    center = [float(top_white_spots_ll.geometry.y.mean()), float(top_white_spots_ll.geometry.x.mean())]
    m = folium.Map(location=center, zoom_start=10, tiles="CartoDB positron")

    folium.GeoJson(
        partidos_ambanorte,
        name="AMBA Norte",
        style_function=lambda _: {
            "fillColor": "#3a86ff",
            "color": "#1d3557",
            "weight": 2,
            "fillOpacity": 0.08,
        },
    ).add_to(m)

    for _, row in clients_ambanorte_ll.iterrows():
        folium.CircleMarker(
            location=[float(row.geometry.y), float(row.geometry.x)],
            radius=4,
            color="#0b4f6c",
            fill=True,
            fill_color="#0b4f6c",
            fill_opacity=0.9,
            tooltip=row.get("Full Address", "Client"),
        ).add_to(m)

    sample_size = min(6000, len(osm_ambanorte_ll))
    if sample_size:
        for _, row in osm_ambanorte_ll.sample(sample_size, random_state=42).iterrows():
            folium.CircleMarker(
                location=[float(row.geometry.y), float(row.geometry.x)],
                radius=1,
                color="#adb5bd",
                fill=True,
                fill_color="#adb5bd",
                fill_opacity=0.5,
                weight=0,
            ).add_to(m)

    for rank, (_, row) in enumerate(top_white_spots_ll.iterrows(), start=1):
        folium.CircleMarker(
            location=[float(row.geometry.y), float(row.geometry.x)],
            radius=6,
            color="#e63946",
            fill=True,
            fill_color="#e63946",
            fill_opacity=0.85,
            popup=(
                f"Rank: {rank}<br>"
                f"Score: {row['white_spot_score']:.3f}<br>"
                f"OSM nearby: {int(row['osm_points_nearby'])}<br>"
                f"Dist to nearest client (m): {int(row['dist_to_nearest_client_m'])}"
            ),
        ).add_to(m)

    folium.LayerControl().add_to(m)
    m.save(output_path)


def map_location_scores(
    clients_ll: gpd.GeoDataFrame,
    osm_in_5km_ll: gpd.GeoDataFrame,
    osm_in_5_10km_ll: gpd.GeoDataFrame,
    output_path: str,
) -> None:
    center = [float(clients_ll.geometry.y.mean()), float(clients_ll.geometry.x.mean())]
    m = folium.Map(location=center, zoom_start=10, tiles="OpenStreetMap", control_scale=True, prefer_canvas=True)

    for _, row in clients_ll.iterrows():
        lat = float(row.geometry.y)
        lon = float(row.geometry.x)
        label = row.get("Full Address", "Client")
        folium.Marker(location=[lat, lon], popup=label, tooltip=label, icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
        folium.Circle(location=[lat, lon], radius=5000, color="#1d4ed8", fill=True, fill_opacity=0.08, weight=1).add_to(m)
        folium.Circle(location=[lat, lon], radius=10000, color="#dc2626", fill=True, fill_opacity=0.04, weight=1).add_to(m)

    for _, row in osm_in_5km_ll.iterrows():
        folium.CircleMarker(
            location=[float(row.geometry.y), float(row.geometry.x)],
            radius=2,
            color="#16a34a",
            fill=True,
            fill_color="#16a34a",
            fill_opacity=0.7,
            weight=0,
        ).add_to(m)

    for _, row in osm_in_5_10km_ll.iterrows():
        folium.CircleMarker(
            location=[float(row.geometry.y), float(row.geometry.x)],
            radius=2,
            color="#f59e0b",
            fill=True,
            fill_color="#f59e0b",
            fill_opacity=0.65,
            weight=0,
        ).add_to(m)

    m.save(output_path)


def map_cannibalization(
    clients_ll: gpd.GeoDataFrame,
    overlap5_geoms: Iterable,
    overlap10_geoms: Iterable,
    coverage_10km,
    output_path: str,
) -> None:
    center = [float(clients_ll.geometry.y.mean()), float(clients_ll.geometry.x.mean())]
    m = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap", control_scale=True, prefer_canvas=True)

    for _, row in clients_ll.iterrows():
        lat = float(row.geometry.y)
        lon = float(row.geometry.x)
        label = f"Client {int(row['client_id'])}: {row['Full Address']}"
        folium.Marker(location=[lat, lon], popup=label, tooltip=label, icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
        folium.Circle(location=[lat, lon], radius=5000, color="#1d4ed8", fill=True, fill_opacity=0.06, weight=1).add_to(m)
        folium.Circle(location=[lat, lon], radius=10000, color="#dc2626", fill=True, fill_opacity=0.03, weight=1).add_to(m)

    for geom in overlap10_geoms:
        geom_ll = gpd.GeoSeries([geom], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]
        folium.GeoJson(
            geom_ll,
            name="Cannibalization 10km overlap",
            style_function=lambda _: {
                "color": "#f59e0b",
                "fillColor": "#f59e0b",
                "fillOpacity": 0.28,
                "weight": 1,
            },
            tooltip="10km overlap zone",
        ).add_to(m)

    for geom in overlap5_geoms:
        geom_ll = gpd.GeoSeries([geom], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]
        folium.GeoJson(
            geom_ll,
            name="Cannibalization 5km overlap",
            style_function=lambda _: {
                "color": "#b91c1c",
                "fillColor": "#ef4444",
                "fillOpacity": 0.45,
                "weight": 1,
            },
            tooltip="5km overlap zone",
        ).add_to(m)

    coverage_ll = gpd.GeoSeries([coverage_10km], crs="EPSG:3857").to_crs(epsg=4326)
    minx, miny, maxx, maxy = coverage_ll.total_bounds
    m.fit_bounds([[float(miny), float(minx)], [float(maxy), float(maxx)]])

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(output_path)
