# From https://github.com/okfn/dptools/blob/master/bin/load-sqlite.py
# No license given in original. Since OKFN assumed to be have open source license.
# 
# Edits by Jeffrey Arnold (2014), BSD-3 
# 
# - converted to Python 3
# 
'''Command line tool to load a Simple Data Format Data Package into sqlite.

For usage do:

    python load-sqlite.py -h
'''
import json
import argparse
import urllib.parse
import os
import sqlite3
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import csv
import codecs

# http://www.sqlite.org/datatype3.html
mappings = {
    'string': 'text',
    'number': 'real',
    'float': 'real',
    'integer': 'integer',
    'date': 'string',
    'boolean': 'integer',
    'date': 'date',
    'datetime': 'datetime'
    }

def load(dpurlOrPath, sqlitePath):
    if not dpurlOrPath.split('://')[0] in ['http', 'https', 'ftp']:
        # it's a path
        dpurl = path2url(dpurlOrPath)
    else:
        dpurl = dpurlOrPath
    # urljoin makes this work right -
    # http://docs.python.org/2/library/urlparse.html#urlparse.urljoin
    dpurl = urllib.parse.urljoin(dpurl, 'datapackage.json')
    basepath = dpurlOrPath.rstrip('datapackage.json')
    dpfo = urllib.request.urlopen(dpurl)
    reader = codecs.getreader("utf-8")
    out = json.load(reader(dpfo))
    for finfo in out['resources']:
        # normalization so we do not have to handle both alternatives
        if not 'url' in finfo:
            finfo['url'] = urllib.parse.urljoin(dpurl, finfo['path'])
        process_resource(finfo, sqlitePath)

def process_resource(finfo, dbpath):
    '''Load the resource specified by finfo into the database at dbpath
    '''
    if 'name' in finfo:
        tablename = finfo['name']
    else:
        _fname = urllib.parse.urlparse(finfo.get('url', ''))[2].split('/')[-1]
        tablename = os.path.splitext(_fname)[0]
    fields = finfo['schema']['fields']
    _columns = ','.join(
            ['"%s" %s' % (field['id'], mappings[field['type']])
                for field in fields]
            )
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    sql = 'CREATE TABLE "%s" (%s)' % (tablename, _columns)
    c.execute(sql)

    _insert_tmpl = 'insert into "%s" values (%s)' % (tablename,
                ','.join(['?']*len(fields)))

    # could do this on but not very robust and will not work on remote urls ...
    # sqlite> .mode csv
    # sqlite> .import <filename> <table>
    req = urllib.request.urlopen(finfo['url'])
    reader = csv.reader(req.read().decode('utf-8').splitlines())
    # skip headers
    for row in reader:
        c.execute(_insert_tmpl, row)
    conn.commit()
    c.close()

def path2url(path):
    return urllib.parse.urljoin(
        'file:', urllib.request.pathname2url(os.path.abspath(path))
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load a data package into sqlite.')
    parser.add_argument('datapackage',
                       help='path to datapackage')
    parser.add_argument('sqlite',
                       help='path to sqlite db')
    args = parser.parse_args() 
    load(args.datapackage, args.sqlite)
