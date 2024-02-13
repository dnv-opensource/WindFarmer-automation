# conda remove --name windfarmer --all --yes
# conda create --name windfarmer python=3.7.10 --yes
# conda activate windfarmer
# conda env update --file environment.yml --prune
# python setup.py bdist_wheel --universal
# final user installation:
#   pip install dist/windfarmer-x.y.z-py2.py3-none-any.whl
# developer installation:
#   pip install -e .
#   conda install -c conda-forge ipykernel=6.8.0
#   python -m ipykernel install --user --name windfarmer

from setuptools import setup, find_packages

setup(
    name='windfarmer',
    version='0.0.1',
    packages=find_packages(),
    description='Windfarmer automation utilities',
    author='Tom Levick',
    author_email='tom.levick@dnv.com',
    maintainer='DNV',
    maintainer_email='renewables.support@dnv.com',
    url='',
    keywords=['wind energy', 'wake model', 'wind farm design', 'windfarmer'],
    #https://pypi.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Customer Service',
        'Environment :: Other Environment',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
    ]
)
