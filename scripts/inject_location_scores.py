import pandas as pd
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'outputs'
POWERBI = OUT / 'powerbi_exports' / 'dim_client_locations.csv'
SCORES = OUT / 'client_location_osm_proximity_scores.csv'
if not POWERBI.exists():
    print('PowerBI client locations not found:', POWERBI)
    raise SystemExit(1)
if not SCORES.exists():
    print('Scores file not found:', SCORES)
    raise SystemExit(1)

pb = pd.read_csv(POWERBI)
s = pd.read_csv(SCORES)
# map Full Address -> location_score
if 'Full Address' in s.columns and 'location_score' in s.columns:
    map_scores = s.set_index('Full Address')['location_score'].to_dict()
elif 'feature_name' in s.columns and 'location_score' in s.columns:
    map_scores = s.set_index('feature_name')['location_score'].to_dict()
else:
    map_scores = {}

# pb uses feature_name column matching Full Address
pb['location_score'] = pb['feature_name'].map(map_scores)
POWERBI.write_text(pb.to_csv(index=False))
print('Updated', POWERBI)
