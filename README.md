# Tensorflow Run Manager

Machine learning engineers often run multiple versions of an algorithm concurrently. However, this can make keeping track of and reproducing runs difficult. This simple utility solves this problem by maintaining a database in human-readable YAML formal that tracks

 - A unique name assigned to each run.
 - A description of each run.
 - The exact command used for the run.
 - The date and time of the run.
 - The most recent commit before the run.

## Installation
# Ubuntu


## Assumptions
This program tries to assume as little about your program as possible, while providing useful functionality. These assumptions are as follows:

- Your program lives in a Git repository.
- The Git working tree is not dirty (if it is, the program will throw an informative error).
- Your program accepts a `--tb-dir` flag pointing to the directory where all tensorboard events are saved and a `--save-path` flag pointing to the directory where model checkpoints are saved.



## Subcommands
For detailed descriptions of each subcommand and its arguments, run
```
runs <subcommand> -h
```

### `new`
Start a new run. This command will

