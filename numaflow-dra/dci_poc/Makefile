test-it:
	PYTHONPATH=../ poetry run pytest -s ../tests/dci_poc/pipeline/ --ignore=../tests/dci_poc/pipeline/test_pipeline_unittest.py

test-setup:
	sudo apt-get -y update
	find . -type f -name apt-packages.txt |\
		xargs -r cat |\
		sed -E '/^\s*$$|^\s*#/d' |\
		sed -E 's/\s*#.*$$//g' |\
		sort |\
		uniq |\
		xargs -r -- sudo apt-get -y install
	poetry install --with dev --no-root
