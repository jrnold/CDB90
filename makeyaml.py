"""
Compile yaml files in ``source/datapackage/`` to ``datapackage.json``
"""
import os
from os import path
import json

import yaml

with open('datapackage.json', 'r') as f:
    data = json.load(f)

for k in data['resources']:
    pathname = k['path']
    resourcename = path.basename(path.splitext(pathname)[0])
    dst = path.join("src/datapackage/resources", "%s.csv" % resourcename)
    with open(dst, 'w') as f:
        yaml.dump(k, f, default_flow_style=False)
