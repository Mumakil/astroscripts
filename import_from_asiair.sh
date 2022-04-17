#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
shopt -s globstar

SOURCE=${1?First argument must be the source dir}
TARGET=${2?Second argument needs to be the target dir}

files=$(ls "$SOURCE"/**/*.fit)
set +e
lights_n=$(echo "$files" | grep -c Light)
biases_n=$(echo "$files" | grep -c Bias)
darks_n=$(echo "$files" | grep -c Dark)
flats_n=$(echo "$files" | grep -c Flat)
set -e

echo "Found ${lights_n} light, ${biases_n} bias, ${darks_n} dark and ${flats_n} flat source images."

echo "Copying to ${TARGET}"

read -e -r -p "Continue? (y/n) " -i "y" CONTINUE

if [ ! "$CONTINUE" = "y" ]; then
  exit 1
fi

mkdir -p "$TARGET"

if [ "$lights_n" -gt 0 ]; then
  targets=$(find "$SOURCE"/**/Light -type d -depth +0 -exec basename {} \;)
  echo "Targets: $(echo "$targets" | tr '\n' ' ')"
  for target in $targets; do
    target_dir="$TARGET/Light/$target"
    lights_batch_n=$(echo "$files" | grep Light | grep -c "$target")
    echo "Copying ${lights_batch_n} lights to ${target_dir}"
    mkdir -p "$target_dir"
    cp "$SOURCE"/**/Light_"$target"*.fit "$target_dir"
  done
fi

if [ "$biases_n" -gt 0 ]; then
  target_dir="$TARGET/Bias"
  echo "Copying ${biases_n} biases to $target_dir"
  mkdir -p "$target_dir"
  cp "$SOURCE"/**/Bias_*.fit "$target_dir"
fi

if [ "$darks_n" -gt 0 ]; then
  target_dir="$TARGET/Dark"
  echo "Copying $darks_n darks to $target_dir"
  mkdir -p "$target_dir"
  cp "$SOURCE"/**/Dark_*.fit "$target_dir"
fi

if [ "$flats_n" -gt 0 ]; then
  target_dir="$TARGET/Flat"
  echo "Copying $flats_n flats to $target_dir"
  mkdir -p "$target_dir"
  cp "$SOURCE"/**/Flat_*.fit "$target_dir"
fi
