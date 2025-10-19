#!/usr/bin/env python3
"""
Session Report Generator for Astrophotography

Analyzes the latest imaging session directory and sends a summary
via Pushover push notification. Works with .xisf files and CSV metadata.

Usage: python session_report.py <root_directory> <pushover_token> <pushover_user>
"""

import csv
import glob
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests


def find_latest_session_directory(root_dir: str) -> Optional[Path]:
    """Find the latest session directory with YYYY-MM-DD format."""
    root_path = Path(root_dir)
    if not root_path.exists():
        print(f"Error: Root directory '{root_dir}' does not exist")
        return None

    # Look for directories matching YYYY-MM-DD pattern
    date_dirs = []
    for item in root_path.iterdir():
        if item.is_dir():
            try:
                # Try to parse as date
                datetime.strptime(item.name, "%Y-%m-%d")
                date_dirs.append(item)
            except ValueError:
                continue

    if not date_dirs:
        print("No session directories found with YYYY-MM-DD format")
        return None

    # Return the most recent one
    return max(date_dirs, key=lambda d: d.name)


def analyze_session_data(session_dir: Path) -> Dict:
    """Analyze session data from .xisf files and CSV metadata."""
    analysis = {
        "by_type": {},
        "by_filter": {},
        "by_target": {},
        "total_exposure_time": 0,
        "date_range": {"start": None, "end": None},
        "targets_info": {},
    }

    # Find all .xisf files
    xisf_patterns = ["*.xisf", "*.XISF"]
    xisf_files = []
    for pattern in xisf_patterns:
        xisf_files.extend(glob.glob(str(session_dir / "**" / pattern), recursive=True))

    # Parse ImageMetaData.csv if it exists
    metadata_csv = session_dir / "ImageMetaData.csv"
    if metadata_csv.exists():
        try:
            with open(metadata_csv, "r") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Extract image type from filename
                    filename = Path(row["FilePath"]).name
                    if filename.startswith("LIGHT_"):
                        img_type = "Light"
                    elif filename.startswith("DARK_"):
                        img_type = "Dark"
                    elif filename.startswith("BIAS_"):
                        img_type = "Bias"
                    elif filename.startswith("FLAT_"):
                        img_type = "Flat"
                    else:
                        img_type = "Unknown"

                    analysis["by_type"][img_type] = (
                        analysis["by_type"].get(img_type, 0) + 1
                    )

                    # Filter
                    filter_name = row.get("FilterName", "No Filter").strip()
                    analysis["by_filter"][filter_name] = (
                        analysis["by_filter"].get(filter_name, 0) + 1
                    )

                    # For calibration frames, use the image type as the target
                    if img_type in ["Dark", "Bias", "Flat"]:
                        target = f"{img_type} frames"
                    else:
                        # Extract target from filename for Light frames
                        # Format: TYPE_YYYY-MM-DD_HH-MM-SS_TargetName_Filter_Temp_Duration_NNNN.xisf
                        filename_parts = filename.replace(".xisf", "").split("_")
                        if len(filename_parts) >= 6:
                            # Target name starts after TIME (index 2) and ends before filter
                            # Find where filter starts by matching against FilterName
                            filter_name_clean = filter_name.replace("/", "-").replace(" ", "-")
                            target_parts = []

                            # Collect parts from index 3 onwards until we hit the filter
                            for i in range(3, len(filename_parts)):
                                part = filename_parts[i]
                                # Check if this part starts the filter name
                                if (
                                    part == filter_name_clean
                                    or part in filter_name
                                    or (
                                        part.startswith("-")
                                        and part[1:].replace(".", "").isdigit()
                                    )
                                    or part.endswith("s")
                                    or part.isdigit()
                                ):
                                    break
                                target_parts.append(part)

                            target = (
                                " ".join(target_parts)
                                if target_parts
                                else "Unknown Target"
                            )
                        else:
                            target = "Unknown Target"

                    analysis["by_target"][target] = (
                        analysis["by_target"].get(target, 0) + 1
                    )

                    # Exposure time
                    try:
                        duration = float(row.get("Duration", 0))
                        analysis["total_exposure_time"] += duration
                    except (ValueError, TypeError):
                        pass

                    # Date/Time
                    exposure_start = row.get("ExposureStartUTC")
                    if exposure_start:
                        if (
                            analysis["date_range"]["start"] is None
                            or exposure_start < analysis["date_range"]["start"]
                        ):
                            analysis["date_range"]["start"] = exposure_start
                        if (
                            analysis["date_range"]["end"] is None
                            or exposure_start > analysis["date_range"]["end"]
                        ):
                            analysis["date_range"]["end"] = exposure_start

        except Exception as e:
            print(f"Warning: Could not process ImageMetaData.csv: {e}")

    # Parse AcquisitionDetails.csv for target information
    acquisition_csv = session_dir / "AcquisitionDetails.csv"
    if acquisition_csv.exists():
        try:
            with open(acquisition_csv, "r") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    target_name = row.get("TargetName", "").strip()
                    if target_name:
                        analysis["targets_info"][target_name] = {
                            "ra": row.get("RACoordinates", ""),
                            "dec": row.get("DECCoordinates", ""),
                            "telescope": row.get("TelescopeName", ""),
                            "focal_length": row.get("FocalLength", ""),
                            "camera": row.get("CameraName", ""),
                        }
        except Exception as e:
            print(f"Warning: Could not process AcquisitionDetails.csv: {e}")

    # Also count any .xisf files that might not be in CSV (like calibration frames)
    if len(xisf_files) > 0:
        # Count files by type from actual filenames
        file_type_counts = {"Light": 0, "Dark": 0, "Bias": 0, "Flat": 0, "Unknown": 0}

        for xisf_file in xisf_files:
            filename = Path(xisf_file).name
            if filename.startswith("LIGHT_"):
                file_type_counts["Light"] += 1
            elif filename.startswith("DARK_"):
                file_type_counts["Dark"] += 1
            elif filename.startswith("BIAS_"):
                file_type_counts["Bias"] += 1
            elif filename.startswith("FLAT_"):
                file_type_counts["Flat"] += 1
            else:
                file_type_counts["Unknown"] += 1

        # Add calibration frames to targets if they exist but weren't in CSV
        for frame_type, count in file_type_counts.items():
            if count > 0 and frame_type in ["Dark", "Bias", "Flat"]:
                target_name = f"{frame_type} frames"
                if target_name not in analysis["by_target"]:
                    analysis["by_target"][target_name] = count
                    analysis["by_type"][frame_type] = count

        # If no CSV data was found at all, report all file counts
        if not analysis["by_target"]:
            for frame_type, count in file_type_counts.items():
                if count > 0:
                    if frame_type in ["Dark", "Bias", "Flat"]:
                        analysis["by_target"][f"{frame_type} frames"] = count
                    else:
                        analysis["by_target"]["Unknown files"] = count
                    analysis["by_type"][frame_type] = count
            print(f"Found {len(xisf_files)} .xisf files but no CSV metadata")

    return analysis


def format_time_duration(seconds: float) -> str:
    """Format seconds into a human-readable duration."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining_seconds = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {remaining_seconds}s"
    elif minutes > 0:
        return f"{minutes}m {remaining_seconds}s"
    else:
        return f"{remaining_seconds}s"


def generate_report_message(session_dir: Path, analysis: Dict) -> str:
    """Generate a formatted report message."""
    session_date = session_dir.name

    message = f"🌟 Imaging Session Report - {session_date}\n\n"

    # Check if we have any data at all
    if not analysis["by_target"] and not analysis["by_type"]:
        message += "No session data found."
        return message

    # Targets (main section)
    if analysis["by_target"]:
        message += "🎯 Targets & Files:\n"
        for target, count in sorted(
            analysis["by_target"].items(), key=lambda x: x[1], reverse=True
        ):
            message += f"  • {target}: {count} frames\n"

    # Image types
    if analysis["by_type"]:
        message += "\n📷 Image Types:\n"
        for img_type, count in sorted(analysis["by_type"].items()):
            message += f"  • {img_type}: {count}\n"

    # Filters
    if analysis["by_filter"]:
        message += "\n🔴 Filters:\n"
        for filter_name, count in sorted(analysis["by_filter"].items()):
            message += f"  • {filter_name}: {count} frames\n"

    # Total exposure time
    if analysis["total_exposure_time"] > 0:
        formatted_time = format_time_duration(analysis["total_exposure_time"])
        message += f"\n⏱️ Total Exposure: {formatted_time}\n"

    # Session duration
    if analysis["date_range"]["start"] and analysis["date_range"]["end"]:
        try:
            start_time = datetime.fromisoformat(
                analysis["date_range"]["start"].replace("T", " ").replace("Z", "")
            )
            end_time = datetime.fromisoformat(
                analysis["date_range"]["end"].replace("T", " ").replace("Z", "")
            )
            duration = end_time - start_time
            duration_str = format_time_duration(duration.total_seconds())
            message += f"\n📅 Session Duration: {duration_str}\n"
        except Exception:
            pass

    return message


def send_pushover_notification(
    token: str,
    user: str,
    message: str,
    title: str = "Astrophotography Session Report",
) -> bool:
    """Send notification via Pushover API."""
    url = "https://api.pushover.net/1/messages.json"

    data = {
        "token": token,
        "user": user,
        "message": message,
        "title": title,
        "priority": 0,
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == 1:
            print("✅ Pushover notification sent successfully")
            return True
        else:
            print(f"❌ Pushover API error: {result}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error sending Pushover notification: {e}")
        return False
    except Exception as e:
        print(f"❌ Error sending Pushover notification: {e}")
        return False


def main() -> None:
    """Main function."""
    if len(sys.argv) != 4:
        print(
            "Usage: python session_report.py <root_directory> "
            "<pushover_token> <pushover_user>"
        )
        print("\nExample:")
        print("  python session_report.py /path/to/sessions abc123token xyz789user")
        print(
            "\nThe script will find the latest YYYY-MM-DD directory in <root_directory>"
        )
        print("and send a summary report via Pushover.")
        sys.exit(1)

    root_directory = sys.argv[1]
    pushover_token = sys.argv[2]
    pushover_user = sys.argv[3]

    # Find latest session directory
    session_dir = find_latest_session_directory(root_directory)
    if not session_dir:
        sys.exit(1)

    print(f"📂 Analyzing session: {session_dir}")

    # Analyze the session
    analysis = analyze_session_data(session_dir)

    # Generate report message
    message = generate_report_message(session_dir, analysis)

    print("\n" + "=" * 50)
    print("REPORT PREVIEW:")
    print("=" * 50)
    print(message)
    print("=" * 50 + "\n")

    # Send notification
    success = send_pushover_notification(pushover_token, pushover_user, message)

    if success:
        print("🎉 Session report sent successfully!")
    else:
        print("💥 Failed to send session report")
        sys.exit(1)


if __name__ == "__main__":
    main()
