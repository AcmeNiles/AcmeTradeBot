.PHONY: test, install, teardown

install:
	@pip install -r requirements.txt

teardown:
	@bash scripts/teardown.sh
