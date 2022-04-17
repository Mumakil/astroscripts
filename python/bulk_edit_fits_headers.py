import os
import sys
from astropy.io import fits

if len(sys.argv) < 4:
    print("Usage: python bulk_edit_fits_headers.py [headername] [value] [files...]")
    exit(1)

header = sys.argv[1]
value = sys.argv[2]
files = sys.argv[3:]

print(f"Setting {header}={value} on {len(files)} files")

for f in files:
    fits.setval(f, header, value=value)
