from shapely.geometry import Point
from shapely.ops import transform
from pyproj import Transformer

# coords from dim_client_locations.csv
a_lat,a_lon = -34.4701088, -58.7754621
b_lat,b_lon = -34.4472279, -58.8668014

tr_to_3857 = Transformer.from_crs('EPSG:4326','EPSG:3857',always_xy=True).transform
tr_to_4326 = Transformer.from_crs('EPSG:3857','EPSG:4326',always_xy=True).transform

pa = Point(tr_to_3857(a_lon,a_lat))
pb = Point(tr_to_3857(b_lon,b_lat))

buf_a = pa.buffer(10000)
buf_b = pb.buffer(10000)
inter = buf_a.intersection(buf_b)
if inter.is_empty:
    print('EMPTY')
else:
    inter_wgs = transform(tr_to_4326, inter)
    print(inter_wgs.wkt)
    # also print area and perimeter in km
    print('area_km2:', inter.area/1_000_000)
    print('perimeter_km:', inter.length/1_000)
