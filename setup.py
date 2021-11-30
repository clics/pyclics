from setuptools import setup, find_packages


setup(
    name='pyclics',
    version='3.0.2',
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.6',
    install_requires=[
        'attrs>=18.1',
        'pylexibank>=2.0',
        'pyconcepticon>=2.2',
        'clldutils>=3.2',
        'pyglottolog>=2.0',
        'geojson',
        'python-igraph>=0.7.1',
        'networkx>=2.1',  # We rely on the `node` attribute
        'unidecode',
        'zope.component',
        'zope.interface',
        'pybtex',
    ],
    extras_require={
        'dev': [
            'tox',
            'flake8',
            'wheel',
            'twine',
        ],
        'test': [
            'pytest>=5.0',
            'pytest-cov',
            'pytest-mock',
            'coverage>=4.2',
        ],
    },
    entry_points={
        'console_scripts': ['clics=pyclics.__main__:main'],
    },
)
