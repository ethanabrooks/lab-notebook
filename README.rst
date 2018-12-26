
.. code:: bash

    runs -y rm % && rm -f runs.db .runsrc

Starting out
============

We begin by creating a new ``.runsrc`` file and creating our database
``runs.db``. Running any ``runs`` command will do this. Note that
without ``--assume-yes``, this would prompt the user for confirmation.
You can also use the short flag ``-y``.

.. code:: bash

    runs --assume-yes ls


.. parsed-literal::

    Config not found. Using default config:
    {'args': '',
     'db_path': '/Users/ethan/lab-notebook/demo/runs.db',
     'dir_names': '',
     'root': '/Users/ethan/lab-notebook/demo/.runs'}
    


.. code:: bash

    ls runs.db  # database that maintains metadata about runs


.. parsed-literal::

    runs.db


.. code:: bash

    cat .runsrc  # config file


.. parsed-literal::

    [main]
    root : /Users/ethan/lab-notebook/demo/.runs
    db_path : /Users/ethan/lab-notebook/demo/runs.db
    dir_names : 
    args : 
    


The ``.runsrc`` establishes various defaults for the ``runs`` command
although these can be overriden with command line arguments. We will
explore some of the capabilities of this file later in the tutorial.

Creating runs
=============

``new``
-------

.. code:: bash

    runs -y new --path=demo --command=python --description="Demonstrate lab-notebook capabilities."


.. parsed-literal::

    [0;32mPath:[0;0m
    demo
    [0;32mDescription:[0;0m
    Demonstrate lab-notebook capabilities.
    [0;32mCommand sent to session:[0;0m
    python
    [0;32mList active:[0;0m
    tmux list-session
    [0;32mAttach:[0;0m
    tmux attach -t demo
    


This performs the following operations: \* Checks for runs with the same
path name and deletes them (after asking permission from the user if no
``-y`` flag). \* Creates a TMUX session with the command launched in it.
\* Stores metadata about the run in ``runs.db``. \* Creates directories
in accordance with ``.runsrc`` (as we demonstrate in the File IO section
of this tutorial).

.. code:: bash

    tmux ls | grep demo


.. parsed-literal::

    demo: 1 windows (created Tue Dec 25 19:36:20 2018) [80x24]


You can create multiple runs with a single run command:

.. code:: bash

    runs -y new --path=demo --command="python dummy.py --flag --my-arg=1 --my-arg=2" \
                --path=demo2 --command="python dummy.py --my-arg=1" \
                --description="Demonstrate creating multiple runs at once"


.. parsed-literal::

    [0;32mPath:[0;0m
    demo2
    [0;32mDescription:[0;0m
    Demonstrate creating multiple runs at once
    [0;32mCommand sent to session:[0;0m
    python dummy.py --my-arg=1
    [0;32mList active:[0;0m
    tmux list-session
    [0;32mAttach:[0;0m
    tmux attach -t demo2
    
    [0;32mPath:[0;0m
    demo
    [0;32mDescription:[0;0m
    Demonstrate creating multiple runs at once
    [0;32mCommand sent to session:[0;0m
    python dummy.py --my-arg=1 --my-arg=2 --flag
    [0;32mList active:[0;0m
    tmux list-session
    [0;32mAttach:[0;0m
    tmux attach -t demo
    


Note that we just overwrote the previous run called ``demo``, meaning
that we killed the associated tmux session and performed various cleanup
actions. Without the ``-y`` flag, it would prompt the user before any
change.

.. code:: bash

    tmux ls | grep demo


.. parsed-literal::

    demo: 1 windows (created Tue Dec 25 19:36:20 2018) [80x24]
    demo2: 1 windows (created Tue Dec 25 19:36:20 2018) [80x24]


Using specs
-----------

You can also use ‘spec’ files to create multiple runs using
cross-products of arguments. You can create a spec file by hand, or you
can generate one from existing runs:

.. code:: bash

    runs to-spec % > run.json  # `%` is a wildcard pattern

.. code:: bash

    cat run.json


.. parsed-literal::

    {
        "args": {
            "my-arg": [
                1,
                [
                    1,
                    2
                ]
            ]
        },
        "command": "python dummy.py",
        "flags": [
            [
                null
            ],
            [
                "flag"
            ]
        ]
    }


Note that ``my-arg`` is a list of lists. This is how specs represent
repeated args.

.. code:: bash

    runs -y from-spec run.json --path=from-spec-demo --description="Demonstrate the use of specs to generate runs."


.. parsed-literal::

    [0;32mPath:[0;0m
    from-spec-demo/0
    [0;32mDescription:[0;0m
    Demonstrate the use of specs to generate runs.
    [0;32mCommand sent to session:[0;0m
    python dummy.py --my-arg="1"
    [0;32mList active:[0;0m
    tmux list-session
    [0;32mAttach:[0;0m
    tmux attach -t from-spec-demo/0
    
    [0;32mPath:[0;0m
    from-spec-demo/1
    [0;32mDescription:[0;0m
    Demonstrate the use of specs to generate runs.
    [0;32mCommand sent to session:[0;0m
    python dummy.py --flag --my-arg="1"
    [0;32mList active:[0;0m
    tmux list-session
    [0;32mAttach:[0;0m
    tmux attach -t from-spec-demo/1
    
    [0;32mPath:[0;0m
    from-spec-demo/2
    [0;32mDescription:[0;0m
    Demonstrate the use of specs to generate runs.
    [0;32mCommand sent to session:[0;0m
    python dummy.py --my-arg="2" --my-arg="1"
    [0;32mList active:[0;0m
    tmux list-session
    [0;32mAttach:[0;0m
    tmux attach -t from-spec-demo/2
    
    [0;32mPath:[0;0m
    from-spec-demo/3
    [0;32mDescription:[0;0m
    Demonstrate the use of specs to generate runs.
    [0;32mCommand sent to session:[0;0m
    python dummy.py --my-arg="2" --flag --my-arg="1"
    [0;32mList active:[0;0m
    tmux list-session
    [0;32mAttach:[0;0m
    tmux attach -t from-spec-demo/3
    


.. code:: bash

    tmux ls | grep demo


.. parsed-literal::

    demo: 1 windows (created Tue Dec 25 19:36:20 2018) [80x24]
    demo2: 1 windows (created Tue Dec 25 19:36:20 2018) [80x24]
    from-spec-demo/0: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/1: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/2: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/3: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]


Querying existing runs
======================

``ls``
------

The most basic way to query runs is simply to list them:

.. code:: bash

    runs ls %  # queries use SQL wildcard patterns ('%' matches everything)


.. parsed-literal::

    demo2
    demo
    from-spec-demo/0
    from-spec-demo/1
    from-spec-demo/2
    from-spec-demo/3


.. code:: bash

    runs ls demo_


.. parsed-literal::

    demo2


You can use ``--active`` to select only runs that have current active
TMUX Sessions

.. code:: bash

    runs ls --active


.. parsed-literal::

    demo
    demo2
    from-spec-demo/0
    from-spec-demo/1
    from-spec-demo/2
    from-spec-demo/3


This matches the output of ``tmux ls``:

.. code:: bash

    tmux ls | grep demo


.. parsed-literal::

    demo: 1 windows (created Tue Dec 25 19:36:20 2018) [80x24]
    demo2: 1 windows (created Tue Dec 25 19:36:20 2018) [80x24]
    from-spec-demo/0: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/1: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/2: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/3: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]


.. code:: bash

    runs -y kill demo

.. code:: bash

    runs ls --active


.. parsed-literal::

    demo2
    from-spec-demo/0
    from-spec-demo/1
    from-spec-demo/2
    from-spec-demo/3


You can also filter by time.

.. code:: bash

    runs ls --since $(date "+%Y-%m-%d")


.. parsed-literal::

    demo2
    demo
    from-spec-demo/0
    from-spec-demo/1
    from-spec-demo/2
    from-spec-demo/3


.. code:: bash

    runs ls --from-last 1day


.. parsed-literal::

    demo2
    demo
    from-spec-demo/0
    from-spec-demo/1
    from-spec-demo/2
    from-spec-demo/3


For info on accepted formats, run ``runs ls -h`` (ommitted for brevity).

All these selection mechanisms are available to other ``runs``
subcommands (``rm``, ``mv``, ``ls``, ``lookup``, ``change-description``,
``reproduce``, ``correlate``, ``kill``).

``lookup``
----------

You can query metadata about runs:

.. code:: bash

    runs lookup command from-spec-demo/%


.. parsed-literal::

    [0;32mfrom-spec-demo/0: [0;0mpython dummy.py --my-arg="1"
    [0;32mfrom-spec-demo/1: [0;0mpython dummy.py --flag --my-arg="1"
    [0;32mfrom-spec-demo/2: [0;0mpython dummy.py --my-arg="2" --my-arg="1"
    [0;32mfrom-spec-demo/3: [0;0mpython dummy.py --my-arg="2" --flag --my-arg="1"


.. code:: bash

    runs lookup datetime from-spec-demo/%


.. parsed-literal::

    [0;32mfrom-spec-demo/0: [0;0m2018-12-25T19:36:22.022499
    [0;32mfrom-spec-demo/1: [0;0m2018-12-25T19:36:22.028994
    [0;32mfrom-spec-demo/2: [0;0m2018-12-25T19:36:22.035280
    [0;32mfrom-spec-demo/3: [0;0m2018-12-25T19:36:22.042038


For info about queryable fields, run ``runs lookup -h`` (omitted for
brevity).

File IO
=======

In this section we will focus on two fields in the ``.runsrc``: \*
``dir_names`` specifies directories that will be placed inside ``root``
and will be synchronized with run paths (created, moved, and deleted
with them). \* ``args`` specifies flags that should be passed to every
run. The ``<path>`` keyword gets replaced with the path of the run.

.. code:: bash

    echo '[main]
    root : /Users/ethan/lab-notebook/demo/.runs
    db_path : /Users/ethan/lab-notebook/demo/runs.db
    dir_names : write-dir
    args : --write-path=${main:root}/write-dir/<path>/hello.txt' > .runsrc

.. code:: bash

    cat file_io_demo.py


.. parsed-literal::

    #! /usr/bin/env python
    
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--write-path', type=Path, required=True)
    args = parser.parse_args()
    
    with args.write_path.open('w') as f:
        f.write('Hello')


.. code:: bash

    runs -y new --path=demo1 --command='python3 file_io_demo.py' \
                --path=demo2 --command='python3 file_io_demo.py' \
                --description='Demonstrate .runsrc capabilities'


.. parsed-literal::

    [0;32mPath:[0;0m
    demo1
    [0;32mDescription:[0;0m
    Demonstrate .runsrc capabilities
    [0;32mCommand sent to session:[0;0m
    python3 file_io_demo.py --write-path=/Users/ethan/lab-notebook/demo/.runs/write-dir/demo1/hello.txt
    [0;32mList active:[0;0m
    tmux list-session
    [0;32mAttach:[0;0m
    tmux attach -t demo1
    
    [0;32mPath:[0;0m
    demo2
    [0;32mDescription:[0;0m
    Demonstrate .runsrc capabilities
    [0;32mCommand sent to session:[0;0m
    python3 file_io_demo.py --write-path=/Users/ethan/lab-notebook/demo/.runs/write-dir/demo2/hello.txt
    [0;32mList active:[0;0m
    tmux list-session
    [0;32mAttach:[0;0m
    tmux attach -t demo2
    


Note that the ``--write-path`` arg has been passed to each run with the
value specified in ``.runsrc``. Also note that the directory
``.runs/write-dir`` was created by the ``runs`` command (because of the
``dir_names`` section in ``.runsrc``), not by ``demo_script.py``:

.. code:: bash

    sleep 1 && tree .runs/write-dir/


.. parsed-literal::

    .runs/write-dir/
    ├── demo1
    │   └── hello.txt
    └── demo2
        └── hello.txt
    
    2 directories, 2 files


.. code:: bash

    tree .runs/write-dir/


.. parsed-literal::

    .runs/write-dir/
    ├── demo1
    │   └── hello.txt
    └── demo2
        └── hello.txt
    
    2 directories, 2 files


In subsequent sections we will see that the program keeps the
``write-dir`` directory in sync with any changes to a run.

Changing runs
=============

``mv``
------

Like the ``new`` command, the ``mv`` command not only renames commands
it also \* Overwrites commands with the same name as the new name for
the run. \* Renames the TMUX session. \* Updates the path name in
``runs.db``. \* Moves directories listed in ``.runsrc`` (as described in
File IO section).

Before we make any changes, let’s remind ourselves of the current state
of things:

.. code:: bash

    runs ls %


.. parsed-literal::

    demo
    from-spec-demo/0
    from-spec-demo/1
    from-spec-demo/2
    from-spec-demo/3
    demo1
    demo2


.. code:: bash

    tmux ls | grep demo  # remember we killed demo


.. parsed-literal::

    demo1: 1 windows (created Tue Dec 25 19:36:27 2018) [80x24]
    demo2: 1 windows (created Tue Dec 25 19:36:27 2018) [80x24]
    from-spec-demo/0: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/1: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/2: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/3: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]


.. code:: bash

    tree .runs  # .runs is empty


.. parsed-literal::

    .runs
    └── write-dir
        ├── demo1
        │   └── hello.txt
        └── demo2
            └── hello.txt
    
    3 directories, 2 files


.. code:: bash

    runs -y mv demo2 demo

This overwrites the run ``demo``. It also moves
``.runs/write-dir/demo2`` and all its contents to
``.runs/write-dir/demo``:

.. code:: bash

    runs ls %


.. parsed-literal::

    from-spec-demo/0
    from-spec-demo/1
    from-spec-demo/2
    from-spec-demo/3
    demo1
    demo


.. code:: bash

    tree .runs  # .runs is empty


.. parsed-literal::

    .runs
    └── write-dir
        ├── demo
        │   └── hello.txt
        └── demo1
            └── hello.txt
    
    3 directories, 2 files


.. code:: bash

    tmux ls | grep demo


.. parsed-literal::

    demo: 1 windows (created Tue Dec 25 19:36:27 2018) [80x24]
    demo1: 1 windows (created Tue Dec 25 19:36:27 2018) [80x24]
    from-spec-demo/0: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/1: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/2: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]
    from-spec-demo/3: 1 windows (created Tue Dec 25 19:36:22 2018) [80x24]


``change-description``
----------------------

We can also change the description for runs

.. code:: bash

    runs change-description from-spec-demo/% 'A new description'

.. code:: bash

    runs lookup description --active


.. parsed-literal::

    [0;32mdemo: [0;0mDemonstrate .runsrc capabilities
    [0;32mdemo1: [0;0mDemonstrate .runsrc capabilities
    [0;32mfrom-spec-demo/0: [0;0mA new description
    [0;32mfrom-spec-demo/1: [0;0mA new description
    [0;32mfrom-spec-demo/2: [0;0mA new description
    [0;32mfrom-spec-demo/3: [0;0mA new description


``kill``
--------

We can also kill the TMUX session for runs without deleting the database
record:

.. code:: bash

    runs -y kill from-spec-demo/%

.. code:: bash

    tmux ls | grep demo


.. parsed-literal::

    demo: 1 windows (created Tue Dec 25 19:36:27 2018) [80x24]
    demo1: 1 windows (created Tue Dec 25 19:36:27 2018) [80x24]


.. code:: bash

    runs ls --active


.. parsed-literal::

    demo
    demo1


.. code:: bash

    runs ls %  # note: runs were not deleted from database


.. parsed-literal::

    from-spec-demo/0
    from-spec-demo/1
    from-spec-demo/2
    from-spec-demo/3
    demo1
    demo


Deleting runs
=============

Finally let’s see what happens when we delete runs.

.. code:: bash

    runs -y rm demo

.. code:: bash

    runs ls %


.. parsed-literal::

    from-spec-demo/0
    from-spec-demo/1
    from-spec-demo/2
    from-spec-demo/3
    demo1


``.runs/write-dir/demo`` and all its contents have been removed.

.. code:: bash

    tree .runs/write-dir/


.. parsed-literal::

    .runs/write-dir/
    └── demo1
        └── hello.txt
    
    1 directory, 1 file


Reproducing runs
================

The ``reproduce`` command prints out commands that will exactly
reproduce a queried run.

.. code:: bash

    runs reproduce demo1


.. parsed-literal::

    [0;32mTo reproduce:[0;0m
    git checkout 0a647b658424035027e8b8f6b239d95c61eb9438
    runs new --path="demo1" --command="python3 file_io_demo.py " --description="Demonstrate .runsrc capabilities"


You can also reproduce multiple runs:

.. code:: bash

    runs reproduce from-spec-demo/%


.. parsed-literal::

    [0;32mTo reproduce:[0;0m
    git checkout 0a647b658424035027e8b8f6b239d95c61eb9438
    runs new \
    --path="from-spec-demo/0" \
    --command="python dummy.py --my-arg=\"1\"" \
    --description="A new description" \
    --path="from-spec-demo/1" \
    --command="python dummy.py --flag --my-arg=\"1\"" \
    --description="A new description" \
    --path="from-spec-demo/2" \
    --command="python dummy.py --my-arg=\"2\" --my-arg=\"1\"" \
    --description="A new description" \
    --path="from-spec-demo/3" \
    --command="python dummy.py --my-arg=\"2\" --flag --my-arg=\"1\"" \
    --description="A new description"


Comparing runs
==============

.. code:: bash

    runs diff from-spec-demo/1 from-spec-demo/2


.. parsed-literal::

    python dummy.py --my-arg="1" [0;32m --flag [0;0m[1;31m --my-arg="2" [0;0m

``runs-git``
============

To do
