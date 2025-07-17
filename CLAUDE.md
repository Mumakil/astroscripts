# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a collection of Python-based astrophotography utilities for processing FITS (Flexible Image Transport System) files. The tools help with header management, file organization, and metadata extraction for astrophotography workflows.

## Architecture

The project uses a simple wrapper pattern:
- Shell scripts in root directory serve as entry points
- Python implementations in `python/` directory handle the actual FITS processing
- All tools use `astropy` library for FITS file manipulation

## Key Commands

### Development Setup
```bash
# Ensure astropy is installed
pip install astropy
```

### Main Tools Usage
```bash
# Bulk edit FITS headers
./bulk_edit_fits_headers.sh [header] [value] [files...]

# Read FITS headers (list all headers if no header specified)
./fits_header.sh [file] [[header]]

# Import and organize files from ASIAir
./import_from_asiair.sh [source] [target]

# Extract metadata to CSV
./statistics.sh [csvfile] [headers] [files...]
```

### Common Usage Patterns
- Use shell glob expansion for batch operations: `./bulk_edit_fits_headers.sh FILTER Ha /path/to/images/*.fit`
- Recommended CSV headers for ASIAir users: `IMAGETYP,INSTRUME,FOCALLEN,FILTER,GAIN,CCD-TEMP,EXPOSURE,DATE-OBS`
- File organization follows astrophotography conventions: Light, Dark, Bias, Flat subdirectories

## Platform Notes

- Designed for macOS (author notes "made for Mac, YMMV elsewhere")
- No formal build system or test suite
- Scripts are directly executable
- Uses standard Python 3 with minimal dependencies

## File Structure

- Shell scripts: Entry points with basic argument handling
- `python/`: Core implementations using astropy
- Target file format: `.fit` FITS files
- Output formats: Modified FITS files or CSV for statistics