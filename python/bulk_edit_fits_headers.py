import os
import sys
from astropy.io import fits

if len(sys.argv) != 4:
    print("Usage: python bulk_edit_fits_headers.py [dir] [headername] [value]")
    exit(1)

target = sys.argv[1]
header = sys.argv[2]
value = sys.argv[3]

files = [f for f in os.listdir(target) if f.endswith(".fit") or f.endswith(".fits")]

print(f"Setting {header}={value} on {len(files)} files")

for f in files:
    fits.setval(target + f, header, value=value)
