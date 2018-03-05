test:
	docker build -t run-manager . && docker run --rm -it run-manager

local-test:
	rm -rf /tmp/test-run-manager && nosetests -w runs/nose
