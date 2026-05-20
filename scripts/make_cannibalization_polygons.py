import csv
from pathlib import Path
from shapely.geometry import Point
from shapely.ops import transform
from pyproj import Transformer
from itertools import combinations

OUT = Path(__file__).resolve().parents[1] / 'outputs' / 'powerbi_exports'
IN = OUT / 'dim_client_locations.csv'
if not IN.exists():
    print('Input dim_client_locations.csv not found')
    raise SystemExit(1)

rows = []
transformer_to_3857 = Transformer.from_crs('EPSG:4326','EPSG:3857',always_xy=True).transform
transformer_to_4326 = Transformer.from_crs('EPSG:3857','EPSG:4326',always_xy=True).transform

# read clients
clients = []
with IN.open(newline='') as f:
    reader = csv.DictReader(f)
    for r in reader:
        if r.get('lat') and r.get('lon'):
            try:
                lat = float(r['lat']); lon = float(r['lon'])
            except Exception:
                continue
            clients.append({'id': int(r['feature_id']), 'name': r['feature_name'], 'lat': lat, 'lon': lon})

for a,b in combinations(clients,2):
    # build points in mercator
    pa = Point(transformer_to_3857(a['lon'], a['lat']))
    pb = Point(transformer_to_3857(b['lon'], b['lat']))
    buf_a = pa.buffer(10000)
    buf_b = pb.buffer(10000)
    inter = buf_a.intersection(buf_b)
    if inter.is_empty:
        continue
    # transform intersection back to 4326
    inter_wgs = transform(transformer_to_4326, inter)
    centroid = inter_wgs.centroid
    rows.append({
        'source_table':'dim_cannibalization_zones',
        'analysis_name':'cannibalization_10km_overlap',
        'feature_type':'polygon',
        'feature_id':f"{a['id']}_{b['id']}_10km",
        'feature_name':f"Client {a['id']} x Client {b['id']}",
        'parent_id':'',
        'lat':centroid.y,
        'lon':centroid.x,
        'geometry_wkt':inter_wgs.wkt,
        'area_km2':inter.area/1_000_000,
        'perimeter_km':inter.length/1_000,
        'metric_1':10000,
        'metric_2':a['id'],
        'metric_3':b['id']
    })

out = OUT / 'dim_cannibalization_zones.csv'
with out.open('w', newline='') as f:
    fieldnames = ['source_table','analysis_name','feature_type','feature_id','feature_name','parent_id','lat','lon','geometry_wkt','area_km2','perimeter_km','metric_1','metric_2','metric_3']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

print('Wrote', out, 'with', len(rows), 'rows')
