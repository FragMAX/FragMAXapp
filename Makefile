all:
	black . --check
	flake8
	./manage.py test
	mypy .

cov:
	coverage erase
	coverage run ./manage.py test
	coverage html -i
