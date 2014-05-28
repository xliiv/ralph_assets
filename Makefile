quicktest:
	DJANGO_SETTINGS_PROFILE=test-assets ralph test ralph_assets

test-with-coveralls:
	DJANGO_SETTINGS_PROFILE=test-assets coverage run --source=ralph_assets --omit='*migrations*,*tests*,*__init__*' '$(VIRTUAL_ENV)/bin/ralph' test ralph_assets

coverage:
	make test-with-coveralls
	coverage html
	coverage report

flake:
	flake8 --exclude="migrations" --statistics src/ralph_assets

runserver:
	ralph runserver
