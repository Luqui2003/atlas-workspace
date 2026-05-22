# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Made the cached Buenos Aires amenities extract opt-in so the pipeline reads the full OSM PBF by default.
- Switched client-buffer filtering to a spatial join so OSM points inside any client buffer are retained.
- Hardened Power BI export scripts to handle WKT reprojection, score injection, and mixed CSV encodings.
- Re-ran the pipeline and refreshed the Power BI exports from the full dataset.

## [0.1.0] - 2026-05-19
- Initial public release (Project Atlas)
- Features: client geocoding, buffer-based cannibalization analysis, white-spot detection, OSM amenity analysis
- Added Power BI export utilities and scripts
- CI: syntax checks

