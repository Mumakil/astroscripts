# Mumakil Astrophotography Scripts

A collection of scripts to assist with astrophotography workflows. These scripts automate tasks like importing files, editing FITS headers, extracting statistics, and organizing data. While these scripts are designed to work on macOS, they may require adjustments for other operating systems.

---

## Table of Contents

- [Overview](#mumakil-astrophotography-scripts)
- [Installation](#installation)
- [Usage](#usage)
  - [bulk_edit_fits_headers.sh](#bulk_edit_fits_headerssh)
  - [import_from_asiair.sh](#import_from_asiairsh)
  - [fits_header.sh](#fits_headersh)
  - [statistics.sh](#statisticssh)
  - [archive_sources.sh](#archive_sourcessh)
  - [session_report.sh](#session_reportsh)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/your-repo/astroscripts.git
    cd astroscripts
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

    This will install:
    - **astropy** (for FITS file processing)
    - **requests** (for Pushover notifications in session_report.sh)

---

## Usage

### `bulk_edit_fits_headers.sh`

Batch add or replace FITS headers in multiple files.

**Usage**:

```bash
bulk_edit_fits_headers.sh [header] [value] [files...]
```

**Parameters**:

- `header`: FITS header name, like `IMGTYP` or `FILTER`.
- `value`: Value to set for the specified header.
- `files`: Target files to operate on. Use shell expansion with globs, e.g., `/Volumes/Astrophotos/**/Light_*.fit`.

**Example**:

```bash
bulk_edit_fits_headers.sh IMGTYP "Light Frame" /Volumes/Astrophotos/**/Light_*.fit
```

---

### `import_from_asiair.sh`

Import and organize FITS files from an ASIAIR memory stick.

**Usage**:

```bash
import_from_asiair.sh [source] [target]
```

**Parameters**:

- `source`: Root folder of the ASIAIR memory stick.
- `target`: Destination folder, e.g., `/Volumes/TRANSCEND/2021-12-21 Testing`.

**Details**:

- Copies FITS files from `source` to `target` subdirectories: `Light`, `Dark`, `Bias`, `Flat`.
- Creates subdirectories under `Light` for different targets.

**Example**:

```bash
import_from_asiair.sh /Volumes/ASIAIR /Volumes/TRANSCEND/2021-12-21
```

---

### `fits_header.sh`

Display FITS header information for a single file.

**Usage**:

```bash
fits_header.sh [file] [[header]]
```

**Parameters**:

- `file`: Path to the FITS file.
- `header` (optional): Specific header to display. If omitted, lists all available headers.

**Example**:

```bash
fits_header.sh example.fits
fits_header.sh example.fits IMGTYP
```

---

### `statistics.sh`

Extract specified FITS headers from multiple files and save them to a CSV file.

**Usage**:

```bash
statistics.sh [csvfile] [headers] [files...]
```

**Parameters**:

- `csvfile`: Path to the output CSV file.
- `headers`: Comma-separated list of FITS headers to include.
- `files`: Glob expression or list of files to process.

**Example**:

```bash
statistics.sh output.csv IMAGETYP,INSTRUME,FOCALLEN,FILTER,GAIN,CCD-TEMP,EXPOSURE,DATE-OBS /Volumes/Astrophotos/**/*.fit
```

---

### `archive_sources.sh`

Sorts astrophotographs into folders with structure `PREFIX/targetname/SESSION_date/files` and includes flat calibration files, taking into account the filter used. Also copies `WeatherData.csv`, `ImageMetaData.csv`, and `AcquisitionDetails.csv` to each destination folder if present.

**Usage**:

#### Single Session

```bash
./archive_sources.sh <source_directory> <destination_directory>
```

#### Batch Mode

```bash
./archive_sources.sh <parent_directory_of_sessions> <destination_directory> --batch
```

- If `--batch` is provided as the third argument, all subdirectories of `<parent_directory_of_sessions>` will be processed as nightly sessions.
- Without `--batch`, only the specified `<source_directory>` will be processed.

---

### `session_report.sh`

Generate and send a comprehensive imaging session report via Pushover push notification.

**Usage**:

```bash
session_report.sh <root_directory> <pushover_token> <pushover_user>
```

**Parameters**:

- `root_directory`: Directory containing YYYY-MM-DD session folders
- `pushover_token`: Your Pushover API token (get from pushover.net)
- `pushover_user`: Your Pushover user key

**Details**:

- Automatically finds the latest YYYY-MM-DD session directory
- Analyzes .xisf files and CSV metadata (ImageMetaData.csv, AcquisitionDetails.csv)
- Reports file counts, image types, targets, filters, exposure time, and session duration
- Sends formatted summary to your phone via Pushover

**Example**:

```bash
session_report.sh /path/to/nightly/sessions abc123token xyz789user
```

**Sample Report**:
```
🌟 Imaging Session Report - 2024-10-17

📁 Total Files: 63

📷 Image Types:
  • Light: 63

🎯 Targets:
  • M 31 Panel 1: 35 frames
  • Barnard 150: 28 frames

🔴 Filters:
  • UV/IR-cut: 63 frames

⏱️ Total Exposure: 5h 15m 0s

📅 Session Duration: 7h 30m 45s
```

---

## Contributing

Contributions are welcome! If you'd like to improve these scripts or add new features:

1. Fork the repository.
2. Create a new branch for your changes.
3. Submit a pull request with a detailed description of your changes.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
