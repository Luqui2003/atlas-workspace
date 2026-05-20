# Project Atlas

[![CI](https://github.com/Luqui2003/geospatial-workspace/actions/workflows/ci.yml/badge.svg)](https://github.com/Luqui2003/geospatial-workspace/actions/workflows/ci.yml)

Project Atlas provides geospatial analysis and visualization tooling for client location analysis, cannibalization detection, and white-spot identification.

## Data Sources
This demo is built for Buenos Aires and uses the following inputs:

- Partidos shapefiles: obtain them from https://catalogo.datos.gba.gob.ar/dataset/partidos/archivo/2cc73f96-98f7-42fa-a180-e56c755cf59a. Equivalent province or district shapefiles for other countries must be obtained separately.
- OSM data: obtain it from Geofabrik at https://download.geofabrik.de/south-america/argentina.html. This source is also intended for Buenos Aires only.
- User location points: provide them in an Excel file with the following columns:
  - Location Name: descriptor of the location. In this example, values are set as "Location 1", "Location 2", ... "Location n".
  - Country: country name for the location.
  - Country Secondary Subdivision: province in this demo. This may need to change if the geography changes.
  - Country Tertiary Subdivision: neighborhood in this demo. This may also need to change if the geography changes.
  - Address: raw address for the location, without country, province, or neighborhood.

## Structure
- `src/data_loading.py`: Data loading functions
- `src/processing.py`: Data processing and geocoding
- `src/visualization.py`: Map creation and export
- `src/main.py`: Pipeline entry point

## Expected Layout
Place the project data in these relative locations:

- `data/partidoslimits/`: partidos shapefiles for Buenos Aires
- `data/osmbsas/`: OSM PBF data from Geofabrik
- `data/`: location Excel files with the columns described above
- `outputs/`: generated HTML maps, CSV exports, and other derived visualizations

## Usage
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Place the required input files in the workspace, using the project-relative paths referenced by the notebook and scripts.
3. Run the pipeline:
   ```
   python -m src.main
   ```
