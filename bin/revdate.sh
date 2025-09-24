#!/bin/bash

affected_files=()
base_rev="${1:-main}"
current_rev="${2:-$(git rev-parse HEAD)}"
files_modified=$(git diff $base_rev..$current_rev --name-only)

for file in $files_modified; do
  if [[ $file == *"/pages/"* ]]; then
    if ! (git diff $base_rev $current_rev $file | grep -q +:revdate); then
      affected_files+=($file)
    fi
  fi
done

if [[ ${#affected_files[@]} -eq 0 ]]; then
  exit 0
else
  for file in ${affected_files[@]}; do
    echo $file
  done
  exit 1
fi

