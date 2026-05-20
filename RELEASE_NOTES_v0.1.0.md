# Project Atlas v0.1.0

Release date: 2026-05-19

Summary:
- Initial public release of Project Atlas. Includes geocoding, buffer-based analysis for cannibalization, white-spot identification, and OSM amenity integration. Exports suitable for Power BI.

Notes for users:
- The repository excludes `outputs/`, `cache/`, and `notebooks/` to protect sample addresses and exports. See `.gitignore`.
- See `CHANGELOG.md` for version history.

How to install:
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

How to run:
```bash
python -m src.main
```

Known limitations:
- Some dependencies require system libraries (GDAL, GEOS, PROJ). For full runtime checks use a container with geospatial libs or install system packages.

Contact: Luqui2003
