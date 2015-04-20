#!/bin/bash

#TODO: make params
git fetch git://github.com/allegro/ralph_assets.git develop:develop
if git diff --quiet develop  -- CHANGES.rst; then
    echo "CHANGES.rst not changed: $? -> exit 1"
    exit 1;
else
    echo "CHANGES.rst changed: $?"
fi
