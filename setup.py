from distutils import core
import cPickle
import os.path
import sys

import pyx12.x12n_document
import pyx12.map_if

map_dir = 'share/pyx12/map'
map_files = [
    'map/270.4010.X092.A1.xml',
    'map/270.4010.X092.xml',
    'map/271.4010.X092.A1.xml',
    'map/271.4010.X092.xml',
    'map/276.4010.X093.A1.xml',
    'map/276.4010.X093.xml',
    'map/277.4010.X093.A1.xml',
    'map/277.4010.X093.xml',
    'map/278.4010.X094.27.A1.xml',
    'map/278.4010.X094.27.xml',
    'map/278.4010.X094.A1.xml',
    'map/278.4010.X094.xml',
    'map/820.4010.X061.A1.xml',
    'map/820.4010.X061.xml',
    'map/834.4010.X095.A1.xml',
    'map/835.4010.X091.A1.xml',
    'map/835.4010.X091.xml',
    'map/837.4010.X096.A1.xml',
    'map/837.4010.X096.xml',
    'map/837.4010.X097.A1.xml',
    'map/837.4010.X097.xml',
    'map/837.4010.X098.A1.xml',
    'map/837.4010.X098.xml',
    'map/841.4010.XXXC.xml',
    'map/997.4010.xml',
    'map/x12.control.00401.xml' 
]
pickle_files = []
for file in map_files:
    pickle_files.append('%s.%s' % (os.path.splitext(file)[0], 'pkl'))

kw = {  
    'name': "pyx12",
    'version': pyx12.x12n_document.__version__,
    'description': pyx12.x12n_document.__doc__,
    #'description': "A X12 validator and converter",
    'author': "John Holland",
    'author_email': "jholland@kazoocmh.org",
    'url': "http://www.sourceforge.net/pyx12/",
    'packages': ['pyx12'],
    'scripts': [ 'bin/x12lint.py', 'bin/x12html.py', 'bin/x12xml.py',
        'bin/x12_build_pkl.py', 'bin/x12norm.py'],
    'data_files': [
        (map_dir, map_files),
        (map_dir, pickle_files),
        (map_dir, ['map/README', 'map/codes.xml', 'map/codes.xsd',
        'map/comp_test.xml', 'map/map.xsd', 'map/maps.xml'])
    ],
      #package_dir = {'': ''},
}

if (hasattr(core, 'setup_keywords') and
    'classifiers' in core.setup_keywords):
    kw['classifiers'] = \
        ['Topic :: Communications, Office/Business',
         'Environment :: Console (Text Based)',
         'Intended Audience :: Developers, Other Audience',
         ' License :: OSI Approved :: BSD License'],

param = pyx12.params.params()
for file in map_files:
    param.set_param('map_path', 'map')
    #param.set_param('pickle_path', 'map')
    map_file = os.path.basename(file)
    print 'Pickling map file %s' % (file)
    pickle_file = '%s.%s' % (os.path.splitext(map_file)[0], 'pkl')
    map = pyx12.map_if.map_if(map_file, param)
    cPickle.dump(map, open(os.path.join('map', pickle_file),'w'))

core.setup(**kw)
