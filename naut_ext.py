# -*- coding: utf-8 -*-
"""
A nautical extension for generate_rbj.py. Basically a wrapper for S57names to allow use of feature class subtypes.

Created by: Hanne L. Petersen <halpe@sdfe.dk>
Created on: 2016-10-10 16:45
"""
import re

import S57names


def is_fcs_abbr(s):
    """Checks if a string matches an s-57 abbreviation pattern (i.e. 6 letters)."""
    obj = re.search('^([A-Z]{6})$', s)
    if obj is None:
        return False
    return True


def get_fcs_number(fcs, fc):
    """Return the subtype number of the feature class subtype."""
    return S57names.S57ABBFC2FCSNumber(fcs, fc)


def get_extended_name(fc, fcs):
    """Return the feature class abbreviation plus long name as e.g. DEPCNT_DepthContour."""
    return S57names.GetExtendedName(fc, fcs)


if __name__ == "__main__":
    pass
