#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
shopt -s globstar

PROJECT=${1?Please give the project as parameter}

TODAY=$(date +%Y-%m-%d)
DATE=${2:-$TODAY}

SOURCE="/Volumes/NO NAME"
WORKSPACE="/Volumes/TRANSCEND"

files=$(ls "$SOURCE"/**/*.fit)
set +e
lights_n=$(echo "$files" | grep -c Light)
biases_n=$(echo "$files" | grep -c Bias)
darks_n=$(echo "$files" | grep -c Dark)
flats_n=$(echo "$files" | grep -c Flat)
set -e

echo "Found ${lights_n} light, ${biases_n} bias, ${darks_n} dark and ${flats_n} flat source images."

WORKSPACE_TARGET="$WORKSPACE/$DATE $PROJECT"
echo "Copying to ${WORKSPACE_TARGET}"

read -e -r -p "Continue? (y/n) " -i "y" CONTINUE

if [ ! "$CONTINUE" = "y" ]; then
  exit 1
fi

mkdir -p "$WORKSPACE_TARGET"

if [ "$lights_n" -gt 0 ]; then
  targets=$(ls "$SOURCE"/**/Light/)
  echo "Targets: $(echo "$targets" | tr '\\n' ' ')"
  echo "Copying ${lights_n} lights to "
  for target in $targets; do
    target_dir="$WORKSPACE_TARGET/Light/$target"
    mkdir -p "$target_dir"
    cp -u "$SOURCE"/**/Light_"$target"*.fit "$target_dir"
  done
fi

if [ "$biases_n" -gt 0 ]; then
  target_dir="$WORKSPACE_TARGET/Bias"
  echo "Copying ${biases_n} biases to $target_dir"
  mkdir -p "$target_dir"
  cp -u "$SOURCE"/**/Bias_*.fit "$target_dir"
fi

if [ "$darks_n" -gt 0 ]; then
  target_dir="$WORKSPACE_TARGET/Dark"
  echo "Copying $darks_n darks to $target_dir"
  mkdir -p "$target_dir"
  cp -u "$SOURCE"/**/Dark_*.fit "$target_dir"
fi

if [ "$flats_n" -gt 0 ]; then
  target_dir="$WORKSPACE_TARGET/Flat"
  echo "Copying $flats_n flats to $target_dir"
  mkdir -p "$target_dir"
  cp -u "$SOURCE"/**/Flat_*.fit "$target_dir"
fi
