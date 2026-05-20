import pandas as pd
from pathlib import Path
OUT = Path(__file__).resolve().parents[1] / 'outputs'
POWERBI = OUT / 'powerbi_exports' / 'dim_client_locations.csv'
SCORES = OUT / 'client_location_osm_proximity_scores.csv'
print('powerbi exists', POWERBI.exists())
print('scores exists', SCORES.exists())
pb = pd.read_csv(POWERBI)
s = pd.read_csv(SCORES)
print('pb cols', pb.columns.tolist())
print('scores cols', s.columns.tolist())
print('scores full address values:')
print(s['Full Address'].tolist())
print('pb feature names:')
print(pb['feature_name'].tolist())
map_scores = s.set_index('Full Address')['location_score'].to_dict()
for name in pb['feature_name']:
    print('mapping for', name, '->', map_scores.get(name))
