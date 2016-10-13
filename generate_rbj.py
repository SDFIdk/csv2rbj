"""
Generator for .rbj files (Data Reviewer Batch Job) for some common rule types.

Reads a .csv file with column headings as input.

This scripts doesn't actually parse the xml that constitutes an .rbj file - instead it
is constructed from chunks of xml, which can be found in the templates folder.

The checktypes dictionary indicates which types of check can be generated.

Author: Hanne L. Petersen, halpe@sdfe.dk
Created: January 2016
Current version: 0.9

TODO:
- Support Check Attributes.
- Allow custom relations for Geometry on Geometry checks.
- Some of the template files are very similar and could be merged and parametrized.
"""
import sys
import os
import string
import uuid
import imp
import re
import arcpy
from datetime import datetime

# If an fc subtype is encountered, use this import to handle it
fcs_extension = os.path.join(os.path.dirname(os.path.realpath(__file__)), "naut_ext.py")

# TODO: use collections.defaultdict: http://stackoverflow.com/questions/3358580/a-forgiving-dictionary
# to allow empty shortname and configkeys
# or do it with objects...
# NOTE: When a new config key is added here, its default value should also be added to _get_param_info()
checktypes = {
    'Invalid Geometry':  # Checktype name
    {
        'geotypes': 'alp',  # Geometry types where this check type is relevant
        'shortname': 'Invalid Geometry',  # Esri's shortname
        'guid': '{00D99404-2FC0-437C-B0C1-B39B507BACC4}',  # Esri DR guid for the check type
        'configkeys': [],  # Configuration keys available for the check type
    },
    'Multipart Line':
    {
        'geotypes': 'l',
        'shortname': 'Multipart Line',
        'guid': '{0AFEF068-ECB2-4CF9-8937-95D45D9528C2}',
        'configkeys': [],
    },
    'Multipart Polygon':
    {
        'geotypes': 'a',
        'shortname': 'Multipart Polygon',
        'guid': '{21C9EA81-1AED-46D0-8CC1-B34F7E6E7855}',
        'configkeys': ['FindMultipleParts', 'FindHoles'],
    },
    'Non-Linear Segment':
    {
        'geotypes': 'al',
        'shortname': 'Non-Linear Segment',
        'guid': '{9F472E55-9799-4CE2-9BDF-CA120E1E4A65}',
        'configkeys': [],
    },
    'Polyline or Path Closes on Self':
    {
        'geotypes': 'l',
        'shortname': 'Polyline or Path Closes on Self',
        'guid': '{F95E2CE9-85A9-443B-8006-7B0B0C03CBC9}',
        'configkeys': ['ErrorTypeIsClosed'],
    },
    'Duplicate Geometry':
    {
        'geotypes': 'alp',
        'shortname': 'Duplicate Geometry',
        'guid': '{5CEFFFB3-AAA1-4A9F-8750-E8D97443F950}',
        'configkeys': ['CheckAttributes', 'ExcludedAttributes', 'IgnorePLTSMetadata'],
    },
    'Duplicate Vertex':
    {
        'geotypes': 'al',
        'shortname': 'Duplicate Vertex',
        'guid': '{1657D1EA-AF38-4B65-B6DE-652D29D61F1D}',
        'configkeys': ['Tolerance', 'ToleranceUnits'],
    },
    'Unique ID':
    {
        'geotypes': 'alp',
        'shortname': 'Unique ID',
        'guid': '{1EF5E608-1B94-4DCF-80B0-5DD6EB855F04}',
        'configkeys': ['DatasetNames', 'FieldItems', 'TablesToQuery'],
    },
    'Geometry on Geometry':
    {
        'geotypes': 'alp',
        'shortname': 'Geo on Geo',
        'guid': '{CA5C29E2-18C9-4702-92A5-6AC810B27181}',
        'configkeys': ['CheckAttributes', 'MergeFeatures', 'NotQuery', 'SpatialEnum'],
        # includes ErrorCondition if CheckAttributes is True
    },
    # '':
    # {
    #     'geotypes': 'alp',
    #     'shortname': '',
    #     'guid': '{}',
    #     'configkeys': [],
    # },
}

# Valid relationships for Geometry on Geometry checks - TODO: relation (Custom relations)
spatial_enums = {'intersects': 1, 'touches': 4, 'overlaps': 5, 'crosses': 6, 'within': 7, 'contains': 8}


def create_batch_rbj_files(infile, db, outfilename=''):
    """
    Create an rbj file with the rules specified in infile.

    If no outfilename is specified, use the infile name with extension changed from .csv to .rbj.
    """
    creator = os.getenv('USERNAME')
    arcpy_version = arcpy.GetInstallInfo()['Version']
    now_str = '{dt.day} {dt:%B} {dt.year}'.format(dt=datetime.now())
    if outfilename == '':
        outfilename = os.path.join(os.path.dirname(infile), os.path.basename(infile)[:-4] + ".rbj")
    with open(infile, 'r') as indata:
        lines = indata.readlines()
    keys = lines[0].strip()
    counter = 1

    filter_guid_string = ''
    datasource_string  = ''
    guid_block2_string = ''
    checkblock_string  = ''
    for line in lines[1:]:  # First line is column headings, so starting on second line
        if line[0:1] == ';':  # Comment line if first character is ;
            continue
        dic = dict(zip(keys.split(';'), line.strip().split(';')))
        if dic['specials']:
            dic['specials'] = dict(i.split("=") for i in dic['specials'].split(","))
        if dic['type'] not in checktypes:  # TODO: check for required keys
            print('Warning: Unknown check type "{}" in {}.\n  Known check types are {}.\n  Skipping...'
                  .format(dic['type'], line, checktypes.keys()))
            continue
        if dic['fc1'] == '':
            print ('Warning: Primary feature class (fc1) must be given. Skipping "{}"...'.format(dic['title']))
            continue
        if dic['type'] == 'Geometry on Geometry' and dic['fc2'] == '':
            print ('Warning: Secondary feature class (fc2) must be given for Geometry on Geometry checks. Skipping "{}"...'
                   .format(dic['title']))
            continue
        counter += 1

        if dic['fcs1'] != '' or dic['fcs2'] != '':  # If there are feature class subtypes, handle them
            fcs_ext = imp.load_source('', fcs_extension)
            if fcs_ext.is_fcs_abbr(dic['fcs1']):
                dic['fcs1'] = fcs_ext.get_fcs_number(dic['fcs1'], dic['fc1'])
            if fcs_ext.is_fcs_abbr(dic['fcs2']):
                dic['fcs2'] = fcs_ext.get_fcs_number(dic['fcs2'], dic['fc2'])
        if dic['severity'] == '':
            dic['severity'] = '3'

        dic['guid1'] = _get_guid_str()
        if len(dic['fc2']) > 0:
            dic['guid2'] = _get_guid_str()

        filter_guid_string += _get_filter_guid(dic['guid1'], dic['fc1'], dic['fcs1'], dic['sql1'])
        datasource_string  += _get_datasource(db, dic['type'], dic['fc1'])
        guid_block2_string += _get_guid_block(db, dic['type'], dic['guid1'], dic['fc1'])
        if len(dic['fc2']) > 0:
            filter_guid_string += "\n" + _get_filter_guid(dic['guid2'], dic['fc2'], dic['fcs2'], dic['sql2'])
            datasource_string  += "\n" + _get_datasource(db, dic['type'], dic['fc2'])
            guid_block2_string += "\n" + _get_guid_block(db, dic['type'], dic['guid2'], dic['fc2'])
        checkblock_string += _get_checkblock(db, dic)

    rbj = _get_file_contents('tpl_outline.txt')

    rbj = rbj.replace('{{BATCHJOBNAME}}', os.path.basename(outfilename))
    rbj = rbj.replace('{{CREATOR}}', creator)
    rbj = rbj.replace('{{CREATIONDATE}}', now_str)
    rbj = rbj.replace('{{EDITOR}}', creator)
    rbj = rbj.replace('{{EDITDATE}}', now_str)
    rbj = rbj.replace('{{BATCHJOBVERSION}}', arcpy_version)
    rbj = rbj.replace('{{GROUPNAME}}', 'Auto-generated DR rules')

    rbj = rbj.replace('{{FILTER_GUIDS}}', filter_guid_string)
    rbj = rbj.replace('{{DATASOURCE}}',   datasource_string)
    rbj = rbj.replace('{{GUID_BLOCK2}}',  guid_block2_string)
    rbj = rbj.replace('{{CHECKBLOCKS}}',  checkblock_string)

    with open(outfilename, 'w') as outf:
        outf.write(rbj)
        print("Wrote file {}.".format(outfilename))


def _get_guid_str():
    """Creates a new random GUID and returns it as a string with curly braces."""
    return '{'+str(uuid.uuid4()).upper()+'}'


def _get_filter_guid(guid, fc, fcs, sql):
    """Return an xml PropertySetProperty block with the guid keys and filters."""
    xml = _get_file_contents('tpl_filter_guid.txt')
    xml = xml.replace('{{GUID}}', guid)
    filters = ''
    if len(sql) > 0:
        filters += _get_sql_filter(fc, sql)
    if len(fcs) > 0:
        filters += _get_subtype_filter(fc, fcs)
    xml = xml.replace('{{FILTERS}}', filters)
    return xml


def _get_sql_filter(fc, sql):
    """Return an xml Filter block with the sql where clause."""
    filt = _get_file_contents('tpl_sqlfilter.txt')
    filt = filt.replace('{{FC}}', fc)
    filt = filt.replace('{{WHERECLAUSE}}', sql.replace("<", "&lt;").replace(">", "&gt;"))
    return filt


def _get_guid_block(dbNam, checktype, guid, fc):
    """Return an xml PropertySetProperty block with the guid keys and database info."""
    if checktype != "Unique ID":
        xml = _get_file_contents('tpl_guid_block.txt')
        xml = xml.replace('{{FC}}', fc)
    else:
        xml = _get_file_contents('tpl_guid_block_for_ids.txt')
        xml = xml.replace('{{FC}}', os.path.basename(dbNam))
    xml = xml.replace('{{GUID}}', guid)
    xml = xml.replace('{{DATABASE}}', dbNam)
    return xml


def _get_checkblock(db, dic):
    """Return an xml RevCheckConfig block with the data from dic."""
    checktype = dic['type']
    cb = _get_file_contents('tpl_checkblock.txt')
    cb = cb.replace('{{GUID}}', dic['guid1'])
    if dic['type'] != "Unique ID":
        cb = cb.replace('{{FC}}', _get_resourcecache(dic['fc1'], dic['fcs1'], dic['fc2'], dic['fcs2']))
    else:
        cb = cb.replace('{{FC}}', _get_resourcecache(os.path.basename(db)))
    cb = cb.replace('{{CHECKTITLE}}', dic['title'])
    cb = cb.replace('{{REVNOTES}}', dic['notes'])
    cb = cb.replace('{{SEVERITY}}', dic['severity'])
    cb = cb.replace('{{CHECKLONGNAME}}', checktype)
    cb = cb.replace('{{REVCHECKGUID}}', checktypes[checktype]['guid'])

    # Some extra info if the rule is comparing two input sources
    block2 = ''
    block3 = ''
    if len(dic['fc2']) > 0:
        block2 = _get_file_contents('tpl_secondary_res_key.txt')
        block2 = block2.replace('{{GUID}}', dic['guid2'])
        block2 = block2.replace('{{CHECKSHORTNAME}}', checktypes[checktype]['shortname'])
        block3 = _get_file_contents('tpl_secondary_key_idx.txt')
        block3 = block3.replace('{{CHECKSHORTNAME}}', checktypes[checktype]['shortname'])
    cb = cb.replace('{{SECONDARYRESKEY}}', block2)
    cb = cb.replace('{{SECONDARYKEYIDX}}', block3)

    # Which configuration keys need to be present depends on the type of check,
    # and sometimes on its parameters (e.g. for Feature on Feature also depends on the spatial relation,
    # Intersect has Tolerance and Tolerance Units)
    configkeys = '\n'.join([_make_xml_string(s) for s in checktypes[checktype]['configkeys']])
    # print("======\n" + configkeys + "\n======")
    checkparams = ''
    for param in checktypes[checktype]['configkeys']:
        checkparams += _get_param_info(param, dic)+"\n"
    # print("======\n" + checkparams + "\n======")
    # if check_attributes:
    #     checkparams += _get_param_info('ErrorConditions', ...)
    cb = cb.replace('{{CHECKPARAMS}}', checkparams)
    cb = cb.replace('{{CONFIGKEYS}}', configkeys)
    cb = cb.replace('{{CHECKCONFIGVERSION}}', str(4+len(checktypes[checktype]['configkeys'])))

    return cb


def _get_subtype_filter(fc, fcs):
    """Returns a subtype filter string, or an empty string if fcs is empty."""
    if fcs == '':
        return ''
    subtypefilter = _get_file_contents('tpl_subtypefilter.txt')
    subtypefilter = subtypefilter.replace('{{FC}}', fc)
    subtypefilter = subtypefilter.replace('{{FCS}}', fcs)
    return subtypefilter


def _get_datasource(database, checktype, fc):
    """Returns a datasource string."""
    browsename = database[1+string.rfind(database, '\\'):-4]  # TODO: use os.path.basename()?
    if checktype != "Unique ID":
        datasrc = _get_file_contents('tpl_datasource.txt')
        datasrc = datasrc.replace('{{FC}}', fc)
    else:
        datasrc = _get_file_contents('tpl_datasource_for_ids.txt')
        datasrc = datasrc.replace('{{FC}}', browsename + ".gdb")
    datasrc = datasrc.replace('{{DATABASE}}', database)
    datasrc = datasrc.replace('{{BROWSENAME}}', browsename)
    return datasrc


def _get_resourcecache(fc1, fcs1='', fc2='', fcs2=''):
    """Return a string with fc/fcs info for ResourceStringCache."""
    if fcs1 != '':
        fcs_ext = imp.load_source('', fcs_extension)
        fc1 = fc1 + ":" + fcs_ext.get_extended_name(fc1, fcs1)
    if fc2 == '':
        return fc1
    if fcs2 != '':
        fcs_ext = imp.load_source('', fcs_extension)
        fc2 = fc2 + ":" + fcs_ext.get_extended_name(fc2, fcs2)
    return fc1 + ', ' + fc2


def _get_param_info(p, dic):
    """
    Return an xml PropertySetProperty block with typical parameter value for parameter.

    The parameter value will be extracted from dic in certain cases:
    - For Geometry on Geometry checks, the spatial relationship is read from dic['specials'].
    - For Unique ID checks, the field name is read from dic['specials'].
    """
    if p == 'CheckAttributes':
        return _param_info_from_tpl(p, 'false', 'xs:boolean')
    elif p == 'IgnorePLTSMetadata':
        return _param_info_from_tpl(p, 'false', 'xs:boolean')
    elif p == 'ExcludedAttributes':
        return _param_info_from_tpl(p, '', 'esri:ArrayOfString')
    elif p == 'MergeFeatures':
        return _param_info_from_tpl(p, 'false', 'xs:boolean')
    elif p == 'NotQuery':
        s = 'false'
        if 'not' in dic['specials']:
            s = 'true'
        return _param_info_from_tpl(p, s, 'xs:boolean')
    elif p == 'SpatialEnum':  # Spatial relationships for Geometry on Geometry
        rel = dic['specials']['Relation']
        obj = re.search('^([a-z ]+)$', rel)
        if obj is None:
            print('Warning: Specials should only contain lowercase letters and spaces for Geometry on Geometry checks, using intersects.')
            rel = 'intersects'
        if rel[:4] == 'not ':
            rel = rel[4:]
        if rel not in spatial_enums:
            print('Warning: Unrecognized relationship "{}" for Geometry on Geometry check, using intersects. Valid values: {}.'.format(rel, spatial_enums.keys()))
            rel = 'intersects'
        return _param_info_from_tpl(p, str(spatial_enums[rel]), 'xs:int')
    elif p == 'Tolerance':
        try:
            val = str(dic['specials']['Tolerance'])
        except TypeError:  # TypeError thrown when dic value is not set
            val = '1'
        return _param_info_from_tpl(p, val, 'xs:double')
    elif p == 'ToleranceUnits':
        try:
            units = {'mm': '7', 'cm': '8', 'm': '9', 'km': '10', 'points': '2'}
            val = units[str(dic['specials']['ToleranceUnits'])]
        except (TypeError, KeyError):  # TypeError thrown when dic value is not set
            print("Couldn't read ToleranceUnit, using cm")
            val = '8'  # default is cm
        return _param_info_from_tpl(p, val, 'xs:int')  # mm = 7; cm = 8; metres = 9; km = 10; points = 2
    elif p == 'FindMultipleParts':
        return _param_info_from_tpl(p, 'true', 'xs:boolean')
    elif p == 'FindHoles':
        return _param_info_from_tpl(p, 'false', 'xs:boolean')
    elif p == 'TablesToQuery':  # Unique ID
        return _param_info_from_tpl(p, _make_xml_string(dic['fc1'].upper()), 'esri:ArrayOfString')
    elif p == 'FieldItems':  # Unique ID
        return _param_info_from_tpl(p, _make_xml_string(dic['specials']['Field']), 'esri:ArrayOfString')
    elif p == 'DatasetNames':  # Unique ID
        return _param_info_from_tpl(p, _make_xml_string(dic['fc1'].upper()), 'esri:ArrayOfString')
    elif p == 'ErrorTypeIsClosed':
        return _param_info_from_tpl(p, 'true', 'xs:boolean')
    # elif p == 'ErrorConditions':  # Check Attributes
    #     rows = ''
    #     for row in ...:
    #         row_comp = get_file_contents('tpl_error_cond_row_comp.txt')
    #         row_comp = row_comp.replace('{{FIELD1}}', f1)
    #         row_comp = row_comp.replace('{{FIELD2}}', f2)
    #         # Possible operators: =, <>, <, <=, >, >=
    #         rows += row_comp
    #     return _param_info_from_tpl(p, rows, 'esri:RowComparisonHelper')
    return ''


def _param_info_from_tpl(key, value, pType):
    """Return an xml PropertySetProperty block with parameter info."""
    param = _get_file_contents('tpl_param_info.txt')
    param = param.replace('{{KEY}}', key)
    param = param.replace('{{VALUE}}', str(value))
    param = param.replace('{{TYPE}}', pType)
    return param


def _make_xml_string(s):
    """Enclose s in <String>...</String>."""
    return '<String>'+s+'</String>'


def _get_file_contents(fnam):
    """Read the contents of file into a string."""
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates', fnam), 'r') as tplfile:
        return tplfile.read()
    return ''


if __name__ == '__main__':
    db = r'C:\arcgis\test\DataReviewer\testdata.gdb'
    rbjfile = ""
    if len(sys.argv) > 3:
        rbjfile = sys.argv[3]
    if len(sys.argv) > 2:
        db = sys.argv[2]
    if len(sys.argv) > 1:
        csvfile = sys.argv[1]
    else:
        csvfile = os.path.join(os.getcwd(), 'demo.csv')

    # db must point to a file-gdb, not sde
    create_batch_rbj_files(csvfile, db)
