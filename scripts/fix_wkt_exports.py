import sys
from pathlib import Path
import pandas as pd
from shapely import wkt
from shapely.ops import transform
from pyproj import Transformer

OUT_DIR = Path(__file__).resolve().parents[1] / 'outputs' / 'powerbi_exports'

if not OUT_DIR.exists():
    print(f"Output dir not found: {OUT_DIR}")
    sys.exit(1)

csvs = list(OUT_DIR.glob('*.csv'))
changed = []
print(f"Found {len(csvs)} CSV files in {OUT_DIR}", flush=True)
for csv in csvs:
    print(f"Inspecting {csv.name}", flush=True)
    try:
        df = pd.read_csv(csv, dtype=str)
    except Exception as e:
        print(f"Skipping {csv.name}: read error {e}", flush=True)
        continue
    if 'geometry_wkt' not in df.columns:
        print(f" - no geometry_wkt column", flush=True)
        continue
    sample = df['geometry_wkt'].dropna().iloc[0] if not df['geometry_wkt'].dropna().empty else None
    if sample is None:
        print(f" - geometry_wkt column empty", flush=True)
        continue
    try:
        geom = wkt.loads(sample)
    except Exception:
        # not a WKT
        print(f" - sample not valid WKT", flush=True)
        continue
    # inspect coordinates
    coords = None
    if hasattr(geom, 'coords'):
        try:
            coords = list(geom.coords)[0]
        except Exception:
            coords = None
    if coords is None:
        # try centroid
        try:
            c = geom.centroid
            coords = list(c.coords)[0]
        except Exception:
            coords = None
    if coords is None:
        print(f" - unable to determine sample coordinates", flush=True)
        continue
    x, y = coords[0], coords[1]
    # if coordinates are large (meters), assume EPSG:3857
    print(f" - sample coords = ({x}, {y})", flush=True)
    if abs(x) > 1000 or abs(y) > 1000:
        print(f"Reprojecting {csv.name} from EPSG:3857 to EPSG:4326", flush=True)
        transformer = Transformer.from_crs(3857, 4326, always_xy=True)
        def reproject_wkt(s):
            if pd.isna(s):
                return s
            try:
                g = wkt.loads(s)
                g2 = transform(transformer.transform, g)
                return g2.wkt
            except Exception:
                return s
        df['geometry_wkt'] = df['geometry_wkt'].apply(reproject_wkt)
        df.to_csv(csv, index=False)
        changed.append(csv.name)

print(f"Processed {len(csvs)} CSVs, updated {len(changed)}: {changed}")
