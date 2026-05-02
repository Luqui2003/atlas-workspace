from pathlib import Path

import geopandas as gpd
import osmium
import pandas as pd


RELEVANT_KEYS = {
    "amenity", "shop", "tourism", "leisure", "office", "craft",
    "public_transport", "building", "landuse", "industrial",
    "healthcare", "education", "brand", "operator",
}

RELEVANT_AMENITY = {
    "hospital", "clinic", "pharmacy", "doctors", "school", "university",
    "college", "bank", "atm", "marketplace", "fuel", "bus_station",
    "parking", "restaurant", "cafe", "fast_food", "bar", "pub",
}

RELEVANT_LEISURE = {"sports_centre", "fitness_centre", "stadium", "park", "mall"}
RELEVANT_TOURISM = {"hotel", "hostel", "guest_house", "attraction", "museum"}
RELEVANT_SHOP = {
    "supermarket", "convenience", "mall", "department_store", "clothes",
    "bakery", "pharmacy", "electronics", "car", "furniture",
}
RELEVANT_LANDUSE = {"commercial", "retail", "industrial", "residential", "mixed"}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (project_root() / candidate).resolve()


def load_locations(excel_path: str | Path) -> pd.DataFrame:
    return pd.read_excel(resolve_path(excel_path))


def load_partidos(partidos_path: str | Path) -> gpd.GeoDataFrame:
    return gpd.read_file(resolve_path(partidos_path))


def _is_relevant(tags_dict: dict) -> bool:
    if any(key in tags_dict for key in RELEVANT_KEYS):
        return True
    if tags_dict.get("amenity") in RELEVANT_AMENITY:
        return True
    if tags_dict.get("shop") in RELEVANT_SHOP:
        return True
    if tags_dict.get("tourism") in RELEVANT_TOURISM:
        return True
    if tags_dict.get("leisure") in RELEVANT_LEISURE:
        return True
    if tags_dict.get("landuse") in RELEVANT_LANDUSE:
        return True
    return False


class RelevantLocationHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        self.total_nodes_seen = 0

    def node(self, n):
        self.total_nodes_seen += 1
        if not n.location.valid() or len(n.tags) == 0:
            return

        tags_dict = dict(n.tags)
        if _is_relevant(tags_dict):
            self.rows.append({
                "id": n.id,
                "type": "node",
                "lat": n.location.lat,
                "lon": n.location.lon,
                "version": n.version,
                "timestamp": str(n.timestamp),
                "changeset": n.changeset,
                "uid": n.uid,
                "user": n.user,
                "tag_count": len(tags_dict),
                "tags": tags_dict,
                "name": tags_dict.get("name"),
            })


def load_osm_relevant_points(pbf_path: str | Path) -> gpd.GeoDataFrame:
    handler = RelevantLocationHandler()
    handler.apply_file(str(resolve_path(pbf_path)), locations=True)

    points_df = pd.DataFrame(handler.rows)
    if points_df.empty:
        return gpd.GeoDataFrame(points_df, geometry=[], crs="EPSG:4326")

    points_df["name"] = points_df["name"].fillna("Unnamed OSM point")
    return gpd.GeoDataFrame(
        points_df,
        geometry=gpd.points_from_xy(points_df["lon"], points_df["lat"]),
        crs="EPSG:4326",
    )


def load_osm_points(pbf_path: str | Path) -> gpd.GeoDataFrame:
    return load_osm_relevant_points(pbf_path)
