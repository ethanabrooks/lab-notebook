test:
	docker build -t run-manager . && docker run --rm -it run-manager

local-test:
	rm -rf /tmp/test-run-manager && python -m unittest runs.tests
