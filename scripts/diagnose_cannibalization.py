from pathlib import Path
import geopandas as gpd
from src.analysis import compute_cannibalization
from src.data_loading import load_locations
from src.processing import add_full_address, geocode_addresses, create_client_geodataframe

root = Path(__file__).resolve().parents[1]
excel_path = root / 'data' / 'Location Example 1.xlsx'
if not excel_path.exists():
    print(f"Client Excel not found at {excel_path}")
    # try to find any excel in data
    for p in (root / 'data').glob('*.xlsx'):
        excel_path = p
        print(f"Using {excel_path}")
        break

print(f"Loading client locations from: {excel_path}")
locations_df = load_locations(excel_path)
locations_df = add_full_address(locations_df)
locations_df = geocode_addresses(locations_df)
client_gdf = create_client_geodataframe(locations_df)
print(f"Loaded {len(client_gdf)} client locations")

if len(client_gdf) < 2:
    print("Not enough clients for cannibalization test")
else:
    result = compute_cannibalization(client_gdf)
    cann_df = result['cannibalization_df']
    overlap5 = result['overlap5_geoms']
    overlap10 = result['overlap10_geoms']
    print(f"Cannibalization pairs: {len(cann_df)}")
    print(f"Overlap5 geometries: {len(overlap5)}")
    print(f"Overlap10 geometries: {len(overlap10)}")
    # show first few rows
    print(cann_df.head().to_string())
    # check if geometries empty
    print('First overlap5 empty?', overlap5[0].is_empty if overlap5 else 'N/A')
    print('First overlap10 empty?', overlap10[0].is_empty if overlap10 else 'N/A')
