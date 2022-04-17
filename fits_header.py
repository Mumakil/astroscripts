import os
import sys
from astropy.io import fits

target = sys.argv[1]

if len(sys.argv) == 2:
  hdul = fits.open(target)
  headers = hdul[0].header
  print(list(headers.keys()))
elif len(sys.argv) == 3:
  header = sys.argv[2]
  value = fits.getval(target, header)
  print(value)
else:
  print("Usage: python fits_header.py [file] [header]")
  exit(1)
