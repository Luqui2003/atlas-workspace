import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from itertools import combinations
from shapely.ops import transform
from pyproj import Transformer
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'outputs' / 'powerbi_exports'
IN = OUT / 'dim_client_locations.csv'
if not IN.exists():
    print('Input dim_client_locations.csv not found')
    raise SystemExit(1)

df = pd.read_csv(IN)
# expect lat, lon columns
if not {'lat','lon'}.issubset(df.columns):
    print('lat/lon columns missing in input')
    raise SystemExit(1)

clients = df[['feature_id','feature_name','lat','lon']].copy()
clients['lat'] = clients['lat'].astype(float)
clients['lon'] = clients['lon'].astype(float)
clients['client_id'] = range(1, len(clients)+1)

# create geodataframe
gdf = gpd.GeoDataFrame(clients, geometry=[Point(xy) for xy in zip(clients['lon'], clients['lat'])], crs='EPSG:4326')
# project to meters
gdf_3857 = gdf.to_crs(epsg=3857)

rows = []
for i,j in combinations(gdf_3857.index, 2):
    a = gdf_3857.loc[i]
    b = gdf_3857.loc[j]
    ov5 = a.geometry.buffer(5000).intersection(b.geometry.buffer(5000))
    ov10 = a.geometry.buffer(10000).intersection(b.geometry.buffer(10000))

    # helper to convert geom to wkt in EPSG:4326
    def to_wkt_wgs84(geom):
        if geom.is_empty:
            return None
        transformer = Transformer.from_crs(3857, 4326, always_xy=True)
        g2 = transform(transformer.transform, geom)
        return g2.wkt

    if not ov5.is_empty:
        centroid = transform(Transformer.from_crs(3857,4326,always_xy=True).transform, ov5.centroid)
        rows.append({
            'source_table':'dim_cannibalization_zones',
            'analysis_name':'cannibalization_5km_overlap',
            'feature_type':'polygon',
            'feature_id':f"{int(a.client_id)}_{int(b.client_id)}_5km",
            'feature_name':f"Client {int(a.client_id)} x Client {int(b.client_id)}",
            'parent_id':None,
            'lat':float(centroid.y),
            'lon':float(centroid.x),
            'geometry_wkt':to_wkt_wgs84(ov5),
            'area_km2':float(ov5.area/1_000_000),
            'perimeter_km':float(ov5.length/1_000),
            'metric_1':5000,
            'metric_2':int(a.client_id),
            'metric_3':int(b.client_id)
        })
    if not ov10.is_empty:
        centroid = transform(Transformer.from_crs(3857,4326,always_xy=True).transform, ov10.centroid)
        rows.append({
            'source_table':'dim_cannibalization_zones',
            'analysis_name':'cannibalization_10km_overlap',
            'feature_type':'polygon',
            'feature_id':f"{int(a.client_id)}_{int(b.client_id)}_10km",
            'feature_name':f"Client {int(a.client_id)} x Client {int(b.client_id)}",
            'parent_id':None,
            'lat':float(centroid.y),
            'lon':float(centroid.x),
            'geometry_wkt':to_wkt_wgs84(ov10),
            'area_km2':float(ov10.area/1_000_000),
            'perimeter_km':float(ov10.length/1_000),
            'metric_1':10000,
            'metric_2':int(a.client_id),
            'metric_3':int(b.client_id)
        })

out = OUT / 'dim_cannibalization_zones.csv'
if rows:
    pd.DataFrame(rows).to_csv(out, index=False)
    print('Wrote', out)
else:
    print('No overlaps found; wrote empty file')
    pd.DataFrame(columns=['source_table','analysis_name','feature_type','feature_id','feature_name','parent_id','lat','lon','geometry_wkt','area_km2','perimeter_km','metric_1','metric_2','metric_3']).to_csv(out, index=False)
    print('Wrote empty', out)
