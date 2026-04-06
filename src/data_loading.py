import pandas as pd
import osmium

def load_locations(excel_path):
    return pd.read_excel(excel_path)

class AmenityHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.points = []
    def node(self, n):
        if any(tag in n.tags for tag in ['amenity', 'shop', 'tourism', 'leisure']):
            if n.location.valid():
                self.points.append((n.location.lat, n.location.lon))

def load_osm_points(pbf_path):
    handler = AmenityHandler()
    handler.apply_file(pbf_path, locations=True)
    return handler.points
