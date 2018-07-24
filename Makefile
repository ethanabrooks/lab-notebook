test:
	docker build -t lab-notebook . && docker run --rm -it lab-notebook

local-test:
	rm -rf /tmp/test-lab-notebook && nosetests -x 

debug-test:
	rm -rf /tmp/test-lab-notebook && ipython --pdb -c "%run /Users/ethan/virtualenvs/sac/bin/nosetests -x -s"

