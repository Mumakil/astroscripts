# Mumakil Astrophotography Scripts

Random scripts to help with astrophotography. I've made these so that they work on my Mac, so if you're not on Mac then YMMV.

## `bulk_edit_fits_headers.sh [header] [value] [files...]`

Add or replace existing fits headers.

* `header` fits header name, like `IMGTYP` or `FILTER`
* `value` value of the header to be set on the images
* `files` target files to operate on. You can use shell expansion with globs to do something like `/Volumes/Astrophotos/**/Light_*.fit`

## `import_from_asiair.sh [source] [target]`

Import all files from asiair memory stick.

* `source` should be the asiair root folder
* `target` can be anything, for example `/Volumes/TRANSCEND/2021-12-21 Testing`

It will then copy every fits file found from `$source` to `$target` subdirectories `Light`, `Dark`, `Bias`, `Flat` and will create subdirectories for different targets under Light as well.

## `fits_header.sh [file] [[header]]`

Print out fits header information of single file. If header is omitted, will list the names of available headers in the file.
