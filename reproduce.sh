#!/usr/bin/env bash

set -e

run_management_dir=$(dirname $(realpath $0))
root=$(dirname ${run_management_dir})

function usage()
{
    echo "Script for reproducing training runs by name."
    echo ""
    echo "./run.sh [name]"
    echo "-h --help"
    echo ""
}

# arg parse
setup_cmd='source venv/bin/activate'
while [[ $# -gt 0 ]]; do
  key="$1"
  case ${key} in
    --help|-h)
      usage
      exit
      ;;
    *)
      name="$1r
      shift
      ;;
  esac
done

if [[ -z name ]]; then
  usage
  exit
fi

branch=$(git rev-parse --abbrev-ref HEAD)
commit=$(python ${run_management_dir}/lookup.py ${name} 'commit')
cmd=$(python ${run_management_dir}/lookup.py ${name} 'command')
git checkout ${commit}
${root}/run.sh ${name} ${cmd}
git checkout ${branch}