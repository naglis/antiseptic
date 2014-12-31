#!/usr/bin/env python

from setuptools import setup


readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

requirements = [
]

test_requirements = [
]

setup(
    name='antiseptic',
    version='0.1.0',
    description='A simple movie directory name cleaner',
    long_description=readme + '\n\n' + history,
    author='Naglis Jonaitis',
    author_email='njonaitis@gmail.com',
    url='https://github.com/naglis/antiseptic',
    packages=[
        'antiseptic',
    ],
    package_dir={'antiseptic': 'antiseptic'},
    include_package_data=True,
    install_requires=requirements,
    license='GPL2',
    zip_safe=False,
    keywords='antiseptic',
    classifiers=[
        'Environment :: Console',
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
    entry_points = { 'console_scripts': [ 'antiseptic = antiseptic.antiseptic:main', ] },
    test_suite='tests',
    tests_require=test_requirements
)
