.PHONY: test, install, teardown

install:
	@pip install -r requirements.txt

test:
	@pytest .

teardown:
	@bash scripts/teardown.sh
