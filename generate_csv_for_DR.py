"""
A helper class for generating Data Reviewer csv files for one or more geodatabases.

Author: Hanne L. Petersen, halpe@sdfe.dk
Created: January 2016
"""
import os
import sys
import csv
import arcpy

import generate_rbj

col_headings = ['type', 'title', 'fc1', 'fcs1', 'sql1', 'fc2', 'fcs2', 'sql2', 'severity', 'notes', 'specials']

# Generate rules for all checks offered by generate_rbj.checktypes, except for the following
# (because these aren't meaningful unless you actually consider their parameters).
skip_checks = ['Unique ID', 'Geometry on Geometry']


def get_fc_shape_type(fc, db=''):
    """
    Get the feature class type of fc, either a, l or p.

    If db is an sde, fc must be prefixed with a data owner. If it's a fgdb, it must not.
    db can be omitted if arcpy.env.workspace is already set.
    """
    print(fc)
    if db != '':
        arcpy.env.workspace = db
    try:
        geotype = arcpy.Describe(fc).shapeType
        return get_shape_type(geotype)
    except IOError:  # fc does not exist
        return -1
    except AttributeError as exc:  # .shapeType attribute does not exist for fc
        print(fc, repr(exc))
        return -1


def get_shape_type(name):
    """Translate the shape type (Polygon, Polyline, Point) into a, l, or p."""
    types = {"Polygon": "a", "Polyline": "l", "Point": "p"}
    try:
        return types[name]
    except KeyError:  # Key not found
        print("Unknown shape type")
        return -1


def generate_csv(conn, folder='generated_rbj', limit_datasets=[]):
    """
    Generates csv files for producing DR checks for a given fgdb schema for all known check types.

    Create a csv file for each check type listed in generate_rbj.checktypes, excluding those in skip_checks.
    Walk through all feature classes in the schema given by conn.
    For each feature class, create an entry in the csv file, if the geometry type matches.

    conn: A fgdb with the structure corresponding to the features classes that should be checked.
    folder: Folder to place generated files in.
    return: An array with file names of the generated csv files.
    """
    print("Starting {}...".format(__file__))
    csv_files = []
    arcpy.env.workspace = conn
    rows = {}
    try:
        os.mkdir(folder)
    except:
        print("Failed to create directory {}.\n  Either it exists already, or there's a problem...".format(folder))
    if isinstance(limit_datasets, basestring):
        limit_datasets = [limit_datasets]

    for ctype in generate_rbj.checktypes:
        if ctype not in skip_checks:
            rows[ctype] = []

    if not limit_datasets:
        limit_datasets = arcpy.ListDatasets(feature_type='feature')

    # Get a list of feature classes
    all_fc = []
    is_fgdb = arcpy.Describe(conn).workspaceFactoryProgID.startswith("esriDataSourcesGDB.FileGDBWorkspaceFactory")
    for ds in limit_datasets:
        all_fc += arcpy.ListFeatureClasses(feature_dataset=ds)

    for fc in all_fc:
        geotype = get_fc_shape_type(fc, conn)
        if '.' in fc:
            fc = fc.split('.')[1]  # dataset was needed in name for getting the shape type, but get rid of it now
        if geotype != -1:
            for ctype in rows:
                specials = ''
                if ctype == "Duplicate Vertex":
                    specials = "Tolerance=5,ToleranceUnits=cm"
                fc2 = '' if ctype != "Duplicate Geometry" else fc
                if geotype in generate_rbj.checktypes[ctype]['geotypes']:
                    rows[ctype].append([ctype, fc + ' ' + ctype.lower(), fc, '', '', fc2, '', '', 3, '', specials])

    for checktype in rows:
        csv_filename = os.path.join(folder, checktype.replace(' ', '_') + '.csv')
        print("Writing {}...".format(csv_filename))
        csv_files.append(csv_filename)
        with open(csv_filename, 'w') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=';', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            # lineterminator = "\n" produces \r\n;
            # lineterminator = \r\n (the default) produces \r\r\n
            csvwriter.writerow(col_headings)
            for row in rows[checktype]:
                csvwriter.writerow(row)
    return csv_files

if __name__ == '__main__':
    my_test_db = r"C:\arcgis\test\DataReviewer\testdata.gdb"  # data location when rbj files are checked in ArcMap

    # Generate default check files for the input database, and place them in a folder at the current location
    if len(sys.argv) >= 2:
        my_db = sys.argv[1]
        my_csvs = generate_csv(my_db, os.path.basename(my_db)[:-4])  # e.g. prod_s100
        for my_csv in my_csvs:
            generate_rbj.create_batch_rbj_files(my_csv, my_test_db)
    else:
        print "Usage: python " + __file__ + " GEODATABASE"

    # # Loop over for several connection files/data owners
    # con_data_owners = [
    #     r'conn_s10.sde',
    #     r'conn_s50.sde',
    #     r'conn_s100.sde',
    # ]
    # for conn in con_data_owners:
    #     scale = conn[1 + str.rindex(conn, '_'):-4]
    #     csvs = generate_csv(conn, scale)
    #     for my_csv in csvs:
    #         generate_rbj.create_batch_rbj_files(my_csv, my_test_db)
