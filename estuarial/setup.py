import os
import sys

if 'develop' in sys.argv:
    # setuptools bad.
    from setuptools import setup
else:
  from distutils.core import setup

curdir = os.path.abspath(os.path.dirname(__file__))
config_suffix_list = ["*.ini"]
catalog_suffix_list = ['*.sql',
                       '*.fsql',
                       '*.fdsql',
                       '*.msql',
                       '*.bsqlspec',
                       '*.sqlspec',
                       '*.py']

def get_sql_files():
    data_files = []

    root = os.path.join("data", "catalog", "SQL_DATA")
    for r, ds, fs in os.walk(root):
        path = r[r.find('SQL_DATA'):]
        sql_files = [os.path.join(path, suf) for suf in catalog_suffix_list]
        data_files = data_files + sql_files

    root = os.path.join("util", "config")
    for r, ds, fs in os.walk(root):
        path = r[r.find('config'):]
        ini_files = [os.path.join(path, suf) for suf in config_suffix_list]
        data_files = data_files + ini_files

    return data_files

package_data = dict(estuarial=get_sql_files())
package_data['estuarial'].append('trqadrc.ini')
package_data['estuarial'].append('estuarial.ini')

version = "0.0.1"
setup(name='estuarial',
      version=version,
      author='Continuum Analytics',
      author_email='info@continuum.io',
      url='http://github.com/ContinuumIO/estuarial',
      description='Python TRQAD API',
      packages=['estuarial',
                'estuarial.test',
                'estuarial.array',
                'estuarial.util',
                'estuarial.util.config',
                'estuarial.data',
                'estuarial.data.query',
                'estuarial.data.browse',
                'estuarial.data.catalog',
                'estuarial.data.drilldown'],
      package_data=package_data,
      zip_safe=False,
      install_requires=['pandas>=0.12.0',
                        'numpy>=1.7.1',
                        'scipy>=0.12.0',
                        'arraymanagement>0.0.1',
                        'pytables>=3.0.0',
                        'sqlalchemy>=0.9.1',
                        'pyodbc>=3.0.7'])