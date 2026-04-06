from data_loading import load_locations, load_osm_points
from processing import add_full_address, geocode_addresses, create_buffers
from visualization import map_with_buffers, map_amenities

def main():
    excel_path = "Location Example 1.xlsx"
    pbf_path = "argentina-260316.osm.pbf"
    df = load_locations(excel_path)
    df = add_full_address(df)
    df = geocode_addresses(df)
    gdf_buffers = create_buffers(df)
    map_with_buffers(gdf_buffers, "mapaconbuffers.html")
    points = load_osm_points(pbf_path)
    map_amenities(points, "argentina_amenities_full.html")

if __name__ == "__main__":
    main()
