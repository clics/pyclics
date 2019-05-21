from setuptools import setup, find_packages


setup(
    name='pyclics',
    version='2.0.0',
    description="creating colexification networks from lexical data",
    long_description=open("README.md").read(),
    long_description_content_type='text/markdown',
    author='Johann-Mattis List and Robert Forkel',
    author_email='clics@shh.mpg.de',
    url='https://github.com/clics/pyclics',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.5',
    install_requires=[
        'attrs>=18.1',
        'pylexibank>=1.1.1',
        'pyconcepticon',
        'pyglottolog',
        'clldutils~=2.0',
        'geojson',
        'python-igraph>=0.7.1',
        'networkx',
        'unidecode',
        'zope.component',
        'zope.interface',
    ],
    extras_require={
        'dev': [
            'tox',
            'flake8',
            'wheel',
            'twine',
        ],
        'test': [
            'mock',
            'pytest>=3.6',
            'pytest-mock',
            'pytest-cov',
            'coverage>=4.2',
        ],
    },
    entry_points={
        'console_scripts': ['clics=pyclics.__main__:main'],
    },
)
