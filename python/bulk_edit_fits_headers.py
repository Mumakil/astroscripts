import os
import glob
import sys
from astropy.io import fits

if len(sys.argv) != 4:
    print("Usage: python bulk_edit_fits_headers.py [glob] [headername] [value]")
    exit(1)

target = sys.argv[1]
header = sys.argv[2]
value = sys.argv[3]

files = list(filter(os.path.isfile, glob.iglob(target, recursive=True)))

print(f"Setting {header}={value} on {len(files)} files")

for f in files:
    fits.setval(f, header, value=value)
