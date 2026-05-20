import importlib.util
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
src_dir = root / 'src'

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

print('Starting safe diagnostic', flush=True)
analysis = load_module('analysis_mod', src_dir / 'analysis.py')
data_loading = load_module('data_loading_mod', src_dir / 'data_loading.py')
processing = load_module('processing_mod', src_dir / 'processing.py')

# find client Excel
excel_path = root / 'data' / 'Location Example 1.xlsx'
if not excel_path.exists():
    for p in (root / 'data').glob('*.xlsx'):
        excel_path = p
        break
print('Using client excel:', excel_path)

locations_df = data_loading.load_locations(excel_path)
locations_df = processing.add_full_address(locations_df)
locations_df = processing.geocode_addresses(locations_df)
client_gdf = processing.create_client_geodataframe(locations_df)
print('Loaded clients:', len(client_gdf))

if len(client_gdf) < 2:
    print('Not enough clients for cannibalization')
    sys.exit(0)

result = analysis.compute_cannibalization(client_gdf)
print('Pairs:', len(result['cannibalization_df']))
print('Overlap5 count:', len(result['overlap5_geoms']))
print('Overlap10 count:', len(result['overlap10_geoms']))
if result['overlap10_geoms']:
    print('First overlap10 area (m^2):', result['overlap10_geoms'][0].area)

# show top of cannibalization df
print(result['cannibalization_df'].head().to_string())
