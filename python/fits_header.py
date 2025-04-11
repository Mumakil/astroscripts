import sys
from astropy.io import fits

target = sys.argv[1]

if len(sys.argv) == 2:
  try:
    hdul = fits.open(target)
  except:
    print ("Error opening the file")
    exit(1)
  headers = hdul[0].header
  try:
    print("\n".join(list(headers.keys())))
  except:
    print("No such header")
    exit(1)
elif len(sys.argv) == 3:
  header = sys.argv[2]
  try:
    value = fits.getval(target, header)
  except:
    print("Could not open file or no such header")
    exit(1)
  print(value)
else:
  print("Usage: python fits_header.py [file] [header]")
  exit(1)
