# -*- encoding: utf-8 -*-

import os
import sys
from setuptools import setup, find_packages

assert sys.version_info >= (2, 7), "Python 2.7+ required."

current_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(current_dir, 'README.rst')) as readme_file:
    with open(os.path.join(current_dir, 'CHANGES.rst')) as changes_file:
        long_description = readme_file.read() + '\n' + changes_file.read()

sys.path.insert(0, current_dir + os.sep + 'src')
from ralph_assets import VERSION
release = ".".join(str(num) for num in VERSION)

setup(
    name='ralph_assets',
    version=release,
    author='Grupa Allegro Sp. z o.o. and Contributors',
    author_email='it-ralph-dev@allegro.pl',
    description="Assets management module for Ralph",
    long_description=long_description,
    url='http://ralph.allegrogroup.com/',
    keywords='',
    platforms=['any'],
    license='Apache Software License v2.0',
    packages=find_packages('src'),
    include_package_data=True,
    package_dir={'': 'src'},
    zip_safe=False,  # because templates are loaded from file path
    install_requires=[
        'ralph>=2.0.0-rc8',
        'django-mptt==0.5.5',
        'xlrd==0.9.2',
        'inkpy==0.1.0-alpha',
        'django-search-forms[ajax]==0.5',
        'factory-boy==2.3.1',
    ],
    entry_points={
        'django.pluggable_app': [
            'assets = ralph_assets.app:Assets',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows :: Windows NT/2000',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
