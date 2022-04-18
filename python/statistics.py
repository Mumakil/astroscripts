import os
import sys
import csv
from astropy.io import fits

if len(sys.argv) < 4:
    print("Usage: python statistics.py [csvfile] [headers] [files...]")
    exit(1)

csvfile = sys.argv[1]
headers = sys.argv[2].split(',')
files = sys.argv[3:]

print("Extracting headers " + ", ".join(headers) + f" from {len(files)} files")

with open(csvfile, 'w', newline='') as cfile:
    writer = csv.writer(cfile)
    writer.writerow(['Path', 'Dirname', 'Basename'] + headers)
    for f in files:
      hdul = fits.open(f)
      hdr = hdul[0].header
      row = [f, os.path.dirname(f), os.path.basename(f)]
      for h in headers:
        try:
          row.append(hdr[h])
        except:
          row.append("N/A")
      writer.writerow(row)
