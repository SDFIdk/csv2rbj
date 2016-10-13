# csv2rbj

Do you also think it's a pain to manage a collection of Data Reviewer batch files for Esri's ArcGIS by using the Reviewer Batch Job Manager in ArcMap? I haven't managed to find any tools (by Esri or others) that help achieve this, so here's my workaround for working more efficiently with Data Reviewer.

csv2rbj simply converts plain text files from a comma-separated format into regular .rbj files. This means you can store and maintain your basic Data Reviewer (DR) rules in a much easier-to-handle format, and then simply generate the .rbj files from that. It also contains a sample module for generating a set of standard rules for a given gdb schema.

Advantages:
* allows you to get an overview of many rules at a glance, e.g. using MS Excel or other spreadsheet software, with a lot fewer mouse clicks.
* because the DR rules are easier to read, csv2rbj allows you to validate your rules more effectively and reduces the risk of click or copy-paste errors going unnoticed.
* opens the possibility of generating many rules automatically by generating csv files, e.g. using Python.

csv2rbj currently handles 9 common DR check types:
* Invalid Geometry
* Multipart Line
* Multipart Polygon
* Non-Linear Segment
* Polyline or Path Closes on Self
* Duplicate Geometry
* Duplicate Vertex
* Unique ID
* Geometry on Geometry

csv2rbj works with Feature Class Subtypes and SQL selection, but doesn't yet include Check Attributes.


## Workflow

A typical workflow including csv2rbj:
1. Use the Reviewer Batch Job Manager to design your rules. Test as you go along.
1. Once you've established your rule, write it down in csv format, and add the similar rules for whatever feature class combinations you need.
1. Convert the rules into rbj, using `generate_rbj.py`.
1. If you want, you can now open the generated rbj files in Reviewer Batch Job Manager to examine your rules, and verify that they look as you expect. (Remember that you must have matching data loaded in the TOC, to properly see the rules.)


## The .csv format used

Each line of the csv file should be semicolon-separated.
The first line of the csv file contains column headings and indicates the field order for the following lines. See the included `demo.csv` for examples of available columns and usages.

Lines starting with semicolon are treated as comments - i.e. a row is a comment if the first spreadsheet cell is empty.

The `specials` column contains parameters that are specific to certain check types. It contains a comma-separated list of = pairs, see demo.csv for examples. Currently it is needed for specifying the `relation` for Geometry on Geometry checks, and the `field` for Unique ID checks.


## Included files

### `generate_rbj.py`

The main functionality for converting csv to rbj.

```Usage: python generate_rbj.py infile.csv database [outfile.rbj]```

#### Parameters

`infile.csv`: Your csv file.

`database`: A file geodatabase containing your data/schema. Note that it must be a **file** geodatabase, not an sde connection. The database is not necessary for basic functionality, but if you want to verify the generated rbj files by opening them in ArcMap's Reviewer Batch Job Manager, it will only display the rules properly, if you have data from the same path loaded in your TOC or fix the paths first (this is true for all rbj files, independently of csv2rbj).

`outfile.rbj`: (Optional) The output rbj file. If omitted, it will use the infile with .csv replaced by .rbj.

### `demo.csv`

A sample csv file illustrating some common types of checks and settings.

### `generate_csv_for_DR.py`

A sample csv generator that takes an input geodatabase (can be an empty schema), and generates csv files with a bunch of standard checks for each feature class, including Invalid Geometry, Duplicate Geometry, etc.

```Usage: python generate_csv_for_DR.py geodatabase```

#### Parameters

`geodatabase`: A file geodatabase with the structure you want.

### `naut_ext.py`

An extension for working with nautical data (S-57) and the feature class subtypes from the Maritime Charting extension for ArcMap. Requires the S57names module or similar.

