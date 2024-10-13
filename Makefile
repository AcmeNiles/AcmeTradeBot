.PHONY: test, install, install-dev, teardown

install:
	@pip install -r requirements/core-requirements.txt

install-dev: install
	@pip install -r requirements/dev-requirements.txt

test:
	@pytest .

teardown:
	@bash scripts/teardown.sh
