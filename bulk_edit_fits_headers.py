import os
from astropy.io import fits

files = os.listdir('./bulk/')

for f in files:
    if f.endswith((".fit")):
        # print(repr(fits.getheader("./bulk/" + f)))
        fits.setval("./bulk/" + f, 'IMAGETYP', value='Dark')
