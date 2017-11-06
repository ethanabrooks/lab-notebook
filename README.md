# Tensorflow Run Manager

Machine learning engineers often run multiple versions of an algorithm concurrently. However, this can make keeping track of and reproducing runs difficult. This simple utility solves this problem by maintaining a database in human-readable YAML formal that tracks

 - A unique name assigned to each run.
 - A description of each run.
 - The exact command used for the run.
 - The date and time of the run.
 - The most recent commit before the run.

## Subcommands

### `new`

