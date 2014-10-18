"""
Compile yaml files in ``source/datapackage/`` to ``datapackage.json``
"""
import os
from os import path
import json

import yaml

SRC_DIR = "src-data/datapackage"
DST_DIR = "."

def create_enum_resource(k, v):
    d = {'path': 'data/enum_%s.csv' % k, 
         'description': v['description'],
         'schema': {'fields': 
                    [{'id': "value", 'description': "variable value", 'type': v['type']}, 
                     {'id': "description", 'description': "description of the value", 'type': 'string'}]}}
    return d

with open(path.join(SRC_DIR, "datapackage.yaml"), 'r') as f:
    data = yaml.load(f)

with open(path.join(SRC_DIR, "..", "version.txt"), 'r') as f:
    data['version'] = f.read().strip()

for file in os.listdir(path.join(SRC_DIR, "resources")):
    if path.splitext(file)[1] == ".yaml":
        with open(path.join(SRC_DIR, "resources", file)) as f:
            resdata = yaml.load(f)
            resdata['name'] = path.splitext(path.basename(resdata['path']))[0]
            data['resources'].append(resdata)
            
with open(path.join(SRC_DIR, 'enum_tables.yaml'), 'r') as f:
    enumdata = yaml.load(f)    
for k, v in enumdata.items():
    data['resources'].append(create_enum_resource(k, v))

with open(path.join(DST_DIR, "datapackage.json"), 'w') as f:
    json.dump(data, f, indent = 2)
