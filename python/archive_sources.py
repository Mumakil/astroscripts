import os
import shutil
import sys
from datetime import datetime, timedelta


def sort_astrophotographs(source_dir, destination_dir):
    """
    Sorts astrophotographs into folders with structure PREFIX/targetname/date/files
    and includes flat calibration files, taking into account the filter used.
    File names are used to extract metadata instead of FITS headers.

    Args:
        source_dir (str): Path to the directory containing raw astrophotographs.
        destination_dir (str): Path to the directory where sorted files will be stored.
    """
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    # Dictionary to store flat files by date and filter
    flats_by_date_and_filter = {}
    # Set to track (session_date, filter_name, target_name) combinations for
    # LIGHT frames
    used_combinations = set()

    # Helper function to parse file names
    def parse_file_name(file_name):
        parts = file_name.split("_")
        if len(parts) < 6:
            raise ValueError(f"Invalid file name format: {file_name}")

        frame_type = parts[0].upper()  # LIGHT or FLAT
        date_str = parts[1]  # Observation date in YYYY-MM-DD format
        time_str = parts[2]  # Observation time in HH-MM-SS format
        target_name = parts[3].replace("\\", " ")  # Target name
        filter_name = parts[4]  # Filter name

        # Combine date and time to determine observation datetime
        observation_datetime = datetime.strptime(
            f"{date_str} {time_str}", "%Y-%m-%d %H-%M-%S"
        )

        # Adjust date to the session start date (evening to following noon)
        if observation_datetime.hour < 12:
            observation_datetime -= timedelta(days=1)

        session_date = observation_datetime.strftime("%Y-%m-%d")

        return frame_type, session_date, target_name, filter_name

    # First pass: Process all files to collect flat frames and move light frames
    for file_name in os.listdir(source_dir):
        if not file_name.lower().endswith((".fits", ".fit", ".xisf")):
            continue  # Skip non-FITS files

        source_file = os.path.join(source_dir, file_name)

        try:
            # Parse metadata from the file name
            frame_type, session_date, target_name, filter_name = parse_file_name(
                file_name
            )

            is_flat = frame_type == "FLAT"
            is_light = frame_type == "LIGHT"

            if is_flat:
                # Store flat files by date and filter
                flats_by_date_and_filter.setdefault(session_date, {}).setdefault(
                    filter_name, []
                ).append(source_file)
                continue

            if not is_light:
                print(f"Skipping unsupported frame type: {file_name}")
                continue

            # Track used (session_date, filter_name, target_name) for LIGHT frames
            used_combinations.add((session_date, filter_name, target_name))

            # Create target-specific folder structure
            # PREFIX/targetname/SESSION_date/files
            target_folder = os.path.join(
                destination_dir, target_name, f"SESSION_{session_date}"
            )
            if not os.path.exists(target_folder):
                os.makedirs(target_folder)

            # Copy the light frame to the target folder
            destination_file = os.path.join(target_folder, file_name)
            shutil.copy(source_file, destination_file)

            print(f"Copied {file_name} to {target_folder}")

        except Exception as e:
            print(f"Error processing file {file_name}: {e}")

    # Second pass: Copy only matching flat frames to their respective target folders
    for session_date, filter_name, target_name in used_combinations:
        target_folder = os.path.join(
            destination_dir, target_name, f"SESSION_{session_date}"
        )
        if os.path.exists(target_folder):
            flat_files = flats_by_date_and_filter.get(session_date, {}).get(
                filter_name, []
            )
            for flat_file in flat_files:
                flat_file_name = os.path.basename(flat_file)
                flat_destination_file = os.path.join(target_folder, flat_file_name)
                if not os.path.exists(flat_destination_file):  # Avoid duplicate copies
                    shutil.copy(flat_file, flat_destination_file)
                    print(f"Copied flat {flat_file_name} to {target_folder}")


if __name__ == "__main__":
    # Replace these paths with your actual source and destination directories
    if len(sys.argv) < 3:
        print(
            "Usage: python archive_sources.py <source_directory> "
            "<destination_directory>"
        )
        sys.exit(1)
    source_directory = sys.argv[1]
    destination_directory = sys.argv[2]

    sort_astrophotographs(source_directory, destination_directory)
