# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.1.1] - 2026-05-21
- Changed OSM loading so the Buenos Aires cached extract is opt-in and the full PBF is used by default.
- Updated client-buffer filtering to use a spatial join so points inside any client buffer are preserved.
- Improved client GeoDataFrame creation by skipping rows without geocoded coordinates with an explicit warning.
- Hardened `scripts/fix_wkt_exports.py` to handle non-point geometries safely when checking/reprojecting WKT.
- Hardened `scripts/inject_location_scores.py` with normalized key matching and mixed-encoding handling for score injection.

## [0.1.0] - 2026-05-19
- Initial public release (Project Atlas)
- Features: client geocoding, buffer-based cannibalization analysis, white-spot detection, OSM amenity analysis
- Added Power BI export utilities and scripts
- CI: syntax checks

