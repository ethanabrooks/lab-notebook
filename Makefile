test:
	docker build -t run-manager . && docker run --rm -it run-manager

local-test:
	rm -rf /tmp/test-run-manager && nosetests -x 

debug-test:
	rm -rf /tmp/test-run-manager && ipython --pdb -c "%run /Users/ethan/virtualenvs/sac/bin/nosetests -x -s"

