#!/usr/bin/env python3
"""
Frame qualification tool for astrophotography sessions.

Reads NINA ImageMetaData.csv and WeatherData.csv to evaluate LIGHT frames
against configurable quality criteria. Falls back to XISF header parsing
for sessions that pre-date the CSV export feature.

With --apply <output-dir>, kept frames are copied to <output-dir>/<relative-path>,
mirroring the session structure. The source archive is never modified.

Usage: python qualify_frames.py [OPTIONS] <directory>
"""

import argparse
import configparser
import csv
import json
import os
import shutil
import struct
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CACHE_FILE = ".qualify_cache.json"

# ──────────────────────────────────────────────────────────── data types ──


@dataclass
class Criteria:
    hfr_max: Optional[float] = None
    fwhm_max: Optional[float] = None
    stars_min: Optional[float] = None
    eccentricity_max: Optional[float] = None
    guiding_rms_max: Optional[float] = None
    adu_median_max: Optional[float] = None
    airmass_max: Optional[float] = None
    sky_quality_min: Optional[float] = None
    cloud_cover_max: Optional[float] = None
    humidity_max: Optional[float] = None

    def any_set(self) -> bool:
        return any(v is not None for v in vars(self).values())


@dataclass
class FrameMetrics:
    hfr: Optional[float] = None
    fwhm: Optional[float] = None
    stars: Optional[float] = None
    eccentricity: Optional[float] = None
    guiding_rms: Optional[float] = None
    adu_median: Optional[float] = None
    airmass: Optional[float] = None
    sky_quality: Optional[float] = None
    cloud_cover: Optional[float] = None
    humidity: Optional[float] = None
    source: str = "csv"  # "csv" or "xisf"


# Human-readable labels for each metric field
METRIC_LABELS: Dict[str, str] = {
    "hfr": "HFR",
    "fwhm": 'FWHM"',
    "stars": "Stars",
    "eccentricity": "Eccen.",
    "guiding_rms": 'Guide"',
    "adu_median": "ADUMed",
    "airmass": "Air",
    "sky_quality": "SQM",
    "cloud_cover": "Cloud%",
    "humidity": "Humid%",
}

# Criteria field -> (metric field, direction)
CRITERIA_MAP: List[Tuple[str, str, str]] = [
    ("hfr_max", "hfr", "max"),
    ("fwhm_max", "fwhm", "max"),
    ("stars_min", "stars", "min"),
    ("eccentricity_max", "eccentricity", "max"),
    ("guiding_rms_max", "guiding_rms", "max"),
    ("adu_median_max", "adu_median", "max"),
    ("airmass_max", "airmass", "max"),
    ("sky_quality_min", "sky_quality", "min"),
    ("cloud_cover_max", "cloud_cover", "max"),
    ("humidity_max", "humidity", "max"),
]

# ─────────────────────────────────────────────────────────────── helpers ──


def parse_float(value: str) -> Optional[float]:
    """Parse a CSV value to float; return None for NaN / empty / invalid."""
    if not value or value.strip().lower() in ("nan", "n/a", ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt(value: Optional[float], spec: str = ".2f") -> str:
    return "-" if value is None else format(value, spec)


# ──────────────────────────────────────────────────────── metadata loaders ──


def load_session_csv(session_dir: Path) -> Dict[str, FrameMetrics]:
    """
    Load ImageMetaData.csv + WeatherData.csv from session_dir.
    Returns a dict keyed by XISF filename (basename only).
    """
    meta_path = session_dir / "ImageMetaData.csv"
    if not meta_path.exists():
        return {}

    # Weather rows indexed by ExposureNumber
    weather: Dict[str, dict] = {}
    weather_path = session_dir / "WeatherData.csv"
    if weather_path.exists():
        try:
            with open(weather_path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    weather[row.get("ExposureNumber", "")] = row
        except Exception:
            pass

    metrics: Dict[str, FrameMetrics] = {}
    try:
        with open(meta_path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                filepath = row.get("FilePath", "")
                if not filepath:
                    continue
                filename = Path(filepath).name
                if not filename.startswith("LIGHT_"):
                    continue

                wrow = weather.get(row.get("ExposureNumber", ""), {})
                metrics[filename] = FrameMetrics(
                    hfr=parse_float(row.get("HFR", "")),
                    fwhm=parse_float(row.get("FWHM", "")),
                    stars=parse_float(row.get("DetectedStars", "")),
                    eccentricity=parse_float(row.get("Eccentricity", "")),
                    guiding_rms=parse_float(row.get("GuidingRMSArcSec", "")),
                    adu_median=parse_float(row.get("ADUMedian", "")),
                    airmass=parse_float(row.get("Airmass", "")),
                    sky_quality=parse_float(wrow.get("SkyQuality", "")),
                    cloud_cover=parse_float(wrow.get("CloudCover", "")),
                    humidity=parse_float(wrow.get("Humidity", "")),
                    source="csv",
                )
    except Exception as e:
        print(f"  Warning: could not read {meta_path.name}: {e}", file=sys.stderr)

    return metrics


def parse_xisf_metrics(path: Path) -> FrameMetrics:
    """Extract metrics from XISF XML header (fallback for sessions without CSV)."""
    m = FrameMetrics(source="xisf")
    try:
        with open(path, "rb") as f:
            if f.read(8) != b"XISF0100":
                return m
            header_len = struct.unpack("<I", f.read(4))[0]
            f.read(4)  # reserved
            xml_data = f.read(header_len)

        root = ET.fromstring(xml_data)
        kw: Dict[str, str] = {}
        for el in root.iter():
            if el.tag.endswith("FITSKeyword"):
                kw[el.get("name", "")] = el.get("value", "").strip("'")

        m.airmass = parse_float(kw.get("AIRMASS", ""))
        m.humidity = parse_float(kw.get("HUMIDITY", ""))
        m.sky_quality = parse_float(kw.get("MPSAS", ""))
        m.cloud_cover = parse_float(kw.get("CLOUDCVR", ""))
    except Exception:
        pass
    return m


# ──────────────────────────────────────────────────────────── evaluation ──


def evaluate_frame(metrics: FrameMetrics, criteria: Criteria) -> Tuple[str, List[str]]:
    """
    Evaluate a frame against all active criteria.
    Returns (decision, reasons) where decision is 'keep', 'discard', or 'no_data'.
    'no_data' means no active criterion had a corresponding metric value.
    """
    failures: List[str] = []
    evaluated = 0

    for crit_field, metric_field, direction in CRITERIA_MAP:
        threshold = getattr(criteria, crit_field)
        if threshold is None:
            continue
        value = getattr(metrics, metric_field)
        if value is None:
            continue
        evaluated += 1
        label = METRIC_LABELS.get(metric_field, metric_field)
        if direction == "max" and value > threshold:
            failures.append(f"{label}={value:.2f}>{threshold:.2f}")
        elif direction == "min" and value < threshold:
            failures.append(f"{label}={value:.2f}<{threshold:.2f}")

    if evaluated == 0:
        return "no_data", []
    return ("discard", failures) if failures else ("keep", [])


# ────────────────────────────────────────────────────────────────── cache ──


def _metrics_to_dict(m: FrameMetrics) -> Dict[str, Any]:
    return {
        "hfr": m.hfr,
        "fwhm": m.fwhm,
        "stars": m.stars,
        "eccentricity": m.eccentricity,
        "guiding_rms": m.guiding_rms,
        "adu_median": m.adu_median,
        "airmass": m.airmass,
        "sky_quality": m.sky_quality,
        "cloud_cover": m.cloud_cover,
        "humidity": m.humidity,
        "source": m.source,
    }


def _metrics_from_dict(d: Dict[str, Any]) -> FrameMetrics:
    return FrameMetrics(
        hfr=d.get("hfr"),
        fwhm=d.get("fwhm"),
        stars=d.get("stars"),
        eccentricity=d.get("eccentricity"),
        guiding_rms=d.get("guiding_rms"),
        adu_median=d.get("adu_median"),
        airmass=d.get("airmass"),
        sky_quality=d.get("sky_quality"),
        cloud_cover=d.get("cloud_cover"),
        humidity=d.get("humidity"),
        source=d.get("source", "unknown"),
    )


def load_cache(session_dir: Path) -> Dict[str, Any]:
    cache_path = session_dir / CACHE_FILE
    if cache_path.exists():
        try:
            with open(cache_path) as f:
                data: Dict[str, Any] = json.load(f)
                return data
        except Exception:
            pass
    return {}


def save_cache(session_dir: Path, cache: Dict[str, Any]) -> None:
    try:
        with open(session_dir / CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"  Warning: could not save cache to {session_dir}: {e}", file=sys.stderr)


# ────────────────────────────────────────────────── session dir discovery ──


def find_session_dirs(root: Path) -> List[Path]:
    """
    Walk root recursively and return all directories that directly contain
    LIGHT_*.xisf files. Skips keep/ and discard/ subdirectories.
    """
    skip = {"rejected"}
    sessions: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip)
        if any(f.startswith("LIGHT_") and f.endswith(".xisf") for f in filenames):
            sessions.append(Path(dirpath))
    return sessions


# ────────────────────────────────────────────────────── session processing ──


def process_session(
    session_dir: Path,
    root: Path,
    criteria: Criteria,
    output_dir: Optional[Path],
    verbose: bool,
) -> Tuple[int, int, int]:
    """Process one session directory. Returns (keep, discard, no_data) counts."""
    light_files = sorted(
        f
        for f in session_dir.iterdir()
        if f.name.startswith("LIGHT_") and f.name.endswith(".xisf")
    )
    if not light_files:
        return 0, 0, 0

    cache = load_cache(session_dir)
    cache_dirty = False
    csv_metrics = load_session_csv(session_dir)
    has_csv = bool(csv_metrics)

    counts = {"keep": 0, "discard": 0, "no_data": 0}
    frame_results: List[Tuple[Path, str, List[str], FrameMetrics]] = []

    for lf in light_files:
        filename = lf.name
        mtime = int(lf.stat().st_mtime)
        cached = cache.get(filename)

        if cached and cached.get("mtime") == mtime:
            m = _metrics_from_dict(cached.get("metrics", {}))
        else:
            m = csv_metrics.get(filename) or parse_xisf_metrics(lf)
            cache[filename] = {"mtime": mtime, "metrics": _metrics_to_dict(m)}
            cache_dirty = True

        decision, reasons = evaluate_frame(m, criteria)

        counts[decision] += 1
        frame_results.append((lf, decision, reasons, m))

    if cache_dirty:
        save_cache(session_dir, cache)

    # Print session summary
    try:
        rel = session_dir.relative_to(root)
    except ValueError:
        rel = session_dir
    src_tag = "CSV" if has_csv else "XISF header"
    k, d, n = counts["keep"], counts["discard"], counts["no_data"]
    print(f"\n{rel}  [{src_tag}]")
    print(f"  {len(light_files)} frames — keep: {k}  discard: {d}  no data: {n}")

    if verbose:
        name_w = 62
        header = (
            f"  {'File':<{name_w}} {'Decision':<9}"
            f" {'HFR':>5} {'FWHM':>6} {'Stars':>6}"
            f" {'Eccen':>6} {'Guide':>6} {'Air':>5}"
            f"  Reasons"
        )
        print(header)
        print("  " + "-" * (len(header) - 2))
        for lf, decision, reasons, m in frame_results:
            tag = {"keep": "keep", "discard": "DISCARD", "no_data": "no data"}[decision]
            row = (
                f"  {lf.name[:name_w]:<{name_w}} {tag:<9}"
                f" {fmt(m.hfr):>5} {fmt(m.fwhm):>6} {fmt(m.stars, '.0f'):>6}"
                f" {fmt(m.eccentricity):>6} {fmt(m.guiding_rms):>6} {fmt(m.airmass):>5}"
            )
            if reasons:
                row += "  " + ", ".join(reasons)
            print(row)

    # Apply: copy kept lights + session flats to output_dir/<rel-path>/
    if output_dir is not None:
        dest_dir = output_dir / session_dir.relative_to(root)

        lights_copied = 0
        for lf, decision, _, _ in frame_results:
            if decision != "keep":
                continue
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / lf.name
            if not dest.exists():
                shutil.copy2(lf, dest)
                lights_copied += 1

        flats_copied = 0
        if lights_copied > 0:
            flat_files = sorted(
                f
                for f in session_dir.iterdir()
                if f.name.startswith("FLAT_") and f.name.endswith(".xisf")
            )
            for ff in flat_files:
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / ff.name
                if not dest.exists():
                    shutil.copy2(ff, dest)
                    flats_copied += 1

        if lights_copied or flats_copied:
            rel = session_dir.relative_to(root)
            dest_display = f"{output_dir}/{rel}" if str(rel) != "." else str(output_dir)
            parts = []
            if lights_copied:
                parts.append(f"{lights_copied} light(s)")
            if flats_copied:
                parts.append(f"{flats_copied} flat(s)")
            print(f"  Copied {', '.join(parts)} → {dest_display}")

    return k, d, n


# ───────────────────────────────────────────────────────────── stats mode ──


def _quantiles(sorted_vals: List[float]) -> List[float]:
    """Return [5th, 25th, 50th, 75th, 95th] percentiles from a sorted list."""
    n = len(sorted_vals)

    def pct(p: float) -> float:
        idx = p / 100 * (n - 1)
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)

    return [pct(5), pct(25), pct(50), pct(75), pct(95)]


def print_stats(sessions: List[Path]) -> None:
    """
    Collect all metric values across sessions and print a distribution table
    to help choose sensible threshold values.
    """
    all_metrics: Dict[str, List[float]] = {f: [] for f in METRIC_LABELS}
    total_frames = 0
    sessions_with_data = 0

    for session_dir in sessions:
        csv_data = load_session_csv(session_dir)
        if not csv_data:
            light_files = sorted(
                f
                for f in session_dir.iterdir()
                if f.name.startswith("LIGHT_") and f.name.endswith(".xisf")
            )
            if not light_files:
                continue
            csv_data = {lf.name: parse_xisf_metrics(lf) for lf in light_files}

        if not csv_data:
            continue

        sessions_with_data += 1
        for m in csv_data.values():
            total_frames += 1
            for field in METRIC_LABELS:
                val = getattr(m, field)
                if val is not None:
                    all_metrics[field].append(val)

    print(
        f"\nMETRIC DISTRIBUTION  ({total_frames} frames, {sessions_with_data} sessions)"
    )
    print()

    cols = ["Metric", "N", "Min", "5th%", "25th%", "Median", "75th%", "95th%", "Max"]
    widths = [10, 6, 8, 8, 8, 8, 8, 8, 8]
    header = "  " + "  ".join(f"{h:<{w}}" for h, w in zip(cols, widths))
    print(header)
    print("  " + "-" * (len(header) - 2))

    for field, label in METRIC_LABELS.items():
        vals = sorted(all_metrics[field])
        if not vals:
            print(f"  {label:<{widths[0]}}  {'0':>{widths[1]}}  (no data)")
            continue
        qs = _quantiles(vals)
        row = [
            label,
            str(len(vals)),
            f"{vals[0]:.2f}",
            f"{qs[0]:.2f}",  # 5th
            f"{qs[1]:.2f}",  # 25th
            f"{qs[2]:.2f}",  # 50th
            f"{qs[3]:.2f}",  # 75th
            f"{qs[4]:.2f}",  # 95th
            f"{vals[-1]:.2f}",
        ]
        print("  " + "  ".join(f"{v:<{w}}" for v, w in zip(row, widths)))


# ─────────────────────────────────────────────────────────────────── main ──


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Qualify astrophotography LIGHT frames by quality criteria.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # See metric distributions to choose thresholds:\n"
            "  qualify_frames.py --stats /path/to/target\n\n"
            "  # Dry-run with criteria:\n"
            "  qualify_frames.py --hfr-max 2.8 --stars-min 500 /path/to/target\n\n"
            "  # Apply — copy kept frames to an output directory:\n"
            "  qualify_frames.py --hfr-max 2.8 --stars-min 500"
            " --apply /output/dir /path/to/target\n"
        ),
    )
    parser.add_argument("directory", help="Directory to scan (recursively)")

    g = parser.add_argument_group("quality criteria (omit to skip that check)")
    g.add_argument("--hfr-max", type=float, metavar="N", help="Max HFR")
    g.add_argument("--fwhm-max", type=float, metavar="N", help="Max FWHM (arcsec)")
    g.add_argument(
        "--stars-min", type=float, metavar="N", help="Min detected star count"
    )
    g.add_argument(
        "--eccentricity-max", type=float, metavar="N", help="Max eccentricity (0-1)"
    )
    g.add_argument(
        "--guiding-rms-max", type=float, metavar="N", help="Max guiding RMS (arcsec)"
    )
    g.add_argument(
        "--adu-median-max", type=float, metavar="N", help="Max background ADU median"
    )
    g.add_argument("--airmass-max", type=float, metavar="N", help="Max airmass")
    g.add_argument(
        "--sky-quality-min",
        type=float,
        metavar="N",
        help="Min sky quality (mag/arcsec^2)",
    )
    g.add_argument(
        "--cloud-cover-max", type=float, metavar="N", help="Max cloud cover %%"
    )
    g.add_argument("--humidity-max", type=float, metavar="N", help="Max humidity %%")

    parser.add_argument(
        "--config",
        metavar="FILE",
        help="INI config file with default criteria (CLI flags override)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print metric distributions to help choose thresholds",
    )
    parser.add_argument(
        "--apply",
        metavar="OUTPUT_DIR",
        help="Copy kept frames to OUTPUT_DIR, mirroring session structure",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Delete all cached decisions before running",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show per-frame detail table"
    )

    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.exists():
        print(f"Error: {args.directory} does not exist", file=sys.stderr)
        sys.exit(1)

    if args.clear_cache:
        cleared = 0
        for dirpath, _, filenames in os.walk(root):
            if CACHE_FILE in filenames:
                (Path(dirpath) / CACHE_FILE).unlink()
                cleared += 1
        print(f"Cleared {cleared} cache file(s).")

    sessions = find_session_dirs(root)
    if not sessions:
        print("No session directories found (looked for dirs containing LIGHT_*.xisf).")
        sys.exit(0)

    # Stats mode
    if args.stats:
        print(f"Scanning {len(sessions)} session(s) in {root} ...")
        print_stats(sessions)
        return

    # Qualify mode

    # Load config file defaults, then let CLI flags override
    cfg: Dict[str, Optional[float]] = {}
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: config file {args.config} not found", file=sys.stderr)
            sys.exit(1)
        cp = configparser.ConfigParser()
        cp.read(config_path)
        section = "qualify_frames"
        if cp.has_section(section):
            for key, val in cp.items(section):
                # Skip comment-only lines (configparser strips them automatically)
                try:
                    cfg[key] = float(val)
                except ValueError:
                    print(
                        f"Warning: ignoring non-numeric config value {key} = {val}",
                        file=sys.stderr,
                    )

    def _get(cli_val: Optional[float], key: str) -> Optional[float]:
        """Return CLI value if provided, else config file value, else None."""
        return cli_val if cli_val is not None else cfg.get(key)

    criteria = Criteria(
        hfr_max=_get(args.hfr_max, "hfr_max"),
        fwhm_max=_get(args.fwhm_max, "fwhm_max"),
        stars_min=_get(args.stars_min, "stars_min"),
        eccentricity_max=_get(args.eccentricity_max, "eccentricity_max"),
        guiding_rms_max=_get(args.guiding_rms_max, "guiding_rms_max"),
        adu_median_max=_get(args.adu_median_max, "adu_median_max"),
        airmass_max=_get(args.airmass_max, "airmass_max"),
        sky_quality_min=_get(args.sky_quality_min, "sky_quality_min"),
        cloud_cover_max=_get(args.cloud_cover_max, "cloud_cover_max"),
        humidity_max=_get(args.humidity_max, "humidity_max"),
    )

    output_dir = Path(args.apply).resolve() if args.apply else None
    mode = f"APPLY → {output_dir}" if output_dir else "DRY RUN"
    print(f"qualify_frames [{mode}]  {root}")
    print(f"Sessions found: {len(sessions)}")

    if not criteria.any_set():
        print("\nNo criteria set — all frames will show as 'no data'.")
        print("Use --stats to see metric distributions, then set thresholds.")
        print()
    else:
        print("Criteria:")
        for crit_field, metric_field, direction in CRITERIA_MAP:
            val = getattr(criteria, crit_field)
            if val is not None:
                label = METRIC_LABELS.get(metric_field, metric_field)
                print(f"  {label} {direction} {val}")
        print()

    total_keep = total_discard = total_no_data = 0
    for session in sessions:
        k, d, n = process_session(session, root, criteria, output_dir, args.verbose)
        total_keep += k
        total_discard += d
        total_no_data += n

    total = total_keep + total_discard + total_no_data
    print(f"\n{'─' * 60}")
    print(f"Total: {total} frames across {len(sessions)} session(s)")
    print(f"  Keep:    {total_keep}")
    print(f"  Discard: {total_discard}")
    print(f"  No data: {total_no_data}")

    # Copy root-level calibration files (master darks, master biases)
    if output_dir and total_keep > 0:
        root_cal = sorted(
            f for f in root.iterdir() if f.is_file() and f.suffix.lower() == ".xisf"
        )
        if root_cal:
            cal_copied = 0
            for cal in root_cal:
                dest = output_dir / cal.name
                if not dest.exists():
                    shutil.copy2(cal, dest)
                    cal_copied += 1
            if cal_copied:
                print(
                    f"\nCopied {cal_copied} master calibration file(s) → {output_dir}"
                )

    if not output_dir and (total_keep + total_discard) > 0:
        print("\nDry run — add --apply <output-dir> to copy kept frames.")


if __name__ == "__main__":
    main()
