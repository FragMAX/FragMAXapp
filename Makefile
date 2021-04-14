all:
	black . --check
	flake8
	./manage.py test
	mypy --config-file mypy.ini .
