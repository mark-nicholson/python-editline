import os
from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

# should cook up a search mechanism to locate a real libedit.so
libedit_base = os.path.sep + os.path.join('scratch', 'mjnichol', 'github', 'python-editline', 'venv')
libedit_inc = os.path.join(libedit_base, 'include')
libedit_lib = os.path.join(libedit_base, 'lib')

# enumerate the items needed
ext_modules = [
    Extension("hello", ["editline/hello.pyx"]),
    Extension("editline.editline", 
              ["editline/editline.pyx"], 
              include_dirs=[libedit_inc],
              library_dirs=[libedit_lib],
              libraries=["edit"]),
    Extension("_editline", 
              ["editline/_editline.c"],
              include_dirs=[libedit_inc],
              library_dirs=[libedit_lib],
              libraries=["edit"])
    ]

# start shovelling...
setup(
    name='EditLine',
    version='0.1.0',
    author='Mark Nicholson',
    author_email='nicholson.mark@gmail.com',
    packages=['editline', 'editline.test'],
    #scripts=['bin/this.py','bin/that.py'],
    url='http://pypi.python.org/pypi/EditLine/',
    license='LICENSE.txt',
    description='Direct interface to libedit for completion support.',
    long_description=open('README.md').read(),
    install_requires=[
        #"Django >= 1.1.1",
        #"caldav == 0.1.4",
    ],
    cmdclass = {'build_ext': build_ext},
    ext_modules = ext_modules,
)
