# Mumakil Astrophotography Scripts

Random scripts to help with astrophotography. I've made these so that they work on my Mac, so if you're not on Mac then YMMV.

## `bulk_edit_fits_headers.py`

Add or replace existing fits headers. Script expects fits files in folder `./bulk/` and will modify them in place. Modify the script to edit the headers you want.

## `import_from_asiair.sh [source] [target]`

Import all files from asiair memory stick.

* `source` should be the asiair root folder
* `target` can be anything, for example `/Volumes/TRANSCEND/2021-12-21 Testing`

It will then copy every fits file found from `$source` to `$target` subdirectories `Light`, `Dark`, `Bias`, `Flat` and will create subdirectories for different targets under Light as well.
