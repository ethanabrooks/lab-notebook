#! /usr/bin/env bash

echo 'runs.yml .runs' > .gitignore
runs new train1
runs new train2
runs ls
runs ls '*1'
runs ls --show-attrs
runs table
# add log-dir flag to config
runs new train1
# open tensorboard
runs lookup description train1
runs lookup commit train1
runs-git checkout #train1
runs reproduce train1
runs mv train1 archive/
runs mv archive/train1 ./
runs mv '*' rldl4/
runs rm 'rldl4/*'
runs ls
# show that tb files have been deleted
