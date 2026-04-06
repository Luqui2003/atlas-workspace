import folium

def map_with_buffers(gdf_buffers, output_path):
    mean_lat = gdf_buffers['lat'].mean()
    mean_lon = gdf_buffers['lon'].mean()
    m = folium.Map(location=[mean_lat, mean_lon], zoom_start=5)
    for _, row in gdf_buffers.iterrows():
        folium.Marker(location=[row['lat'], row['lon']], popup=row['Full Address']).add_to(m)
        folium.Circle(location=[row['lat'], row['lon']], radius=5000, color='blue', fill=True, fill_opacity=0.2).add_to(m)
        folium.Circle(location=[row['lat'], row['lon']], radius=10000, color='red', fill=True, fill_opacity=0.2).add_to(m)
    m.save(output_path)

def map_amenities(points, output_path):
    m = folium.Map(location=[-34.6, -58.4], zoom_start=5)
    for lat, lon in points:
        folium.CircleMarker(location=[lat, lon], radius=1, fill=True).add_to(m)
    m.save(output_path)
