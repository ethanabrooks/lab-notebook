#! /usr/bin/env bash

echo 'runs.yml .runs' > .gitignore
runs new train1 'python -m baselines.ppo2.run_mlp' --description='demo lab-notebook'
# show runs.yml
# show tmux
# New config: 
# virtualenv-path
# dir_names
# flags
runs new train1 'python -m baselines.ppo2.run_mlp' --description='demo lab-notebook'
runs new train2 'python -m baselines.ppo2.run_mlp' --description='demo lab-notebook'
runs ls
runs ls '*1'
runs ls --show-attrs
runs table
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
