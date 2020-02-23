"""Useful constants for running auxTel"""
from lsst.geom import ExtentD, PointD

plateScale = 0.101              # exp.getWcs().getPixelScale().asArcseconds()  # arcsec/pixel

boreSight = PointD(2036.5, 2000.5)    # boreSight on detector (pixels)
sweetSpots = {                  # the sweet spots for the gratings (pixels)
    'ronchi90lpmm' : PointD(1780, 1800),
}
gratingOffsets = {              # image motion when we insert a grating (pixels)
    'empty_1' : ExtentD(0, 0),
    'empty_4' : ExtentD(0, 0),
    'ronchi90lpmm' : ExtentD(200, 20),
}

dFocusDthickness = 0.0075628    # Number of mm of focus change per mm of glass thickness

glassThicknesses = {            # The thicknesses of our filters and gratings (mm)
    'empty_1' :      0.0,
    'empty_4' :      0.0,
    'ronchi90lpmm' : 6.0,
    'BG40' :         3.0,
    'RG610' :        3.0,
    'quadnotch1' :   3.5,
}
