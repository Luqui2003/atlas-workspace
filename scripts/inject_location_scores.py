import pandas as pd
from pathlib import Path
import unicodedata

OUT = Path(__file__).resolve().parents[1] / 'outputs'
POWERBI = OUT / 'powerbi_exports' / 'dim_client_locations.csv'
SCORES = OUT / 'client_location_osm_proximity_scores.csv'
if not POWERBI.exists():
    print('PowerBI client locations not found:', POWERBI)
    raise SystemExit(1)
if not SCORES.exists():
    print('Scores file not found:', SCORES)
    raise SystemExit(1)

def norm_key(s: object) -> str:
    if pd.isna(s):
        return ""
    return unicodedata.normalize('NFKC', str(s)).strip()

# read scores with latin1 to avoid mojibake from mixed encodings
s = pd.read_csv(SCORES, encoding='latin1')
# read PowerBI export as UTF-8 to preserve correct accents
pb = pd.read_csv(POWERBI, encoding='utf-8')

map_scores = {}
def add_key(k, v):
    nk = norm_key(k)
    map_scores[nk] = v
    # try to repair common mojibake (when UTF-8 bytes were decoded as latin1)
    try:
        repaired = k.encode('latin1').decode('utf-8')
        map_scores[norm_key(repaired)] = v
    except Exception:
        pass

if 'location_score' in s.columns:
    if 'Full Address' in s.columns:
        for k, v in s.set_index('Full Address')['location_score'].to_dict().items():
            add_key(k, v)
    elif 'feature_name' in s.columns:
        for k, v in s.set_index('feature_name')['location_score'].to_dict().items():
            add_key(k, v)

# apply normalized mapping to feature_name
pb['location_score'] = pb['feature_name'].apply(lambda v: map_scores.get(norm_key(v), None))

# write back using utf-8
pb.to_csv(POWERBI, index=False, encoding='utf-8')
print('Updated', POWERBI)
