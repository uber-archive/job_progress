all: develop test release

test: develop lint
	py.test

t:
	py.test

bootstrap:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install -r requirements-test.txt

develop:
	python setup.py develop

release: clean test
	prerelease && release
	git push
	git push --tags
	echo "Now upload to the internal PyPi"

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +

lint:
	flake8 job_progress

coverage:
	coverage run --source job_progress setup.py test
	coverage report -m
	coverage html
	open htmlcov/index.html

docs: develop clean
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

docs_open: docs
	open docs/_build/html/index.html
