#! /usr/bin/env bash

#echo 'runs.yml .runs' > .gitignore
#runs new train1 'python -m baselines.ppo2.run_mlp' --description='demo lab-notebook'
# show runs.yml
# show tmux

echo '[filesystem]
root = /Users/ethan/baselines/.runs
db_path = /Users/ethan/baselines/runs.yml
dir_names = tensorboard
virtualenv_path = /Users/ethan/virtualenvs/baselines
hidden_columns = input_command

[flags]
--logdir=${filesystem:root}/tensorboard/<path>

[new]
description = demo lab-notebook
' > .runsrc

runs new train1 'python -m baselines.ppo2.run_mlp' --description='demo lab-notebook'
runs new train2 'python -m baselines.ppo2.run_mlp' --description='demo lab-notebook'
runs ls
runs ls '*1'
runs ls --show-attrs
runs table --column-width=15
# open tensorboard
runs lookup description train1
runs lookup commit train1
runs-git diff +train1
runs-git checkout +train1
runs reproduce train1
runs mv train1 archive/
# Show file structure
runs ls
runs mv archive/train1 ./
runs mv '*' rldl4/
runs rm 'rldl4/*'
runs ls
# show that tb files have been deleted
