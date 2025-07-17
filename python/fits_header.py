import sys

from astropy.io import fits

target = sys.argv[1]

if len(sys.argv) == 2:
    try:
        hdul = fits.open(target)
    except Exception as e:
        print(f"Error opening the file: {e}")
        exit(1)
    headers = hdul[0].header
    try:
        print("\n".join(list(headers.keys())))
    except Exception as e:
        print(f"No such header: {e}")
        exit(1)
elif len(sys.argv) == 3:
    header = sys.argv[2]
    try:
        value = fits.getval(target, header)
    except Exception as e:
        print(f"Could not open file or no such header: {e}")
        exit(1)
    print(value)
else:
    print("Usage: python fits_header.py [file] [header]")
    exit(1)
