import asyncio
import numpy as np

import lsst.geom as geom
from lsst.observing.constants import plateScale
from lsst.observing.utils.misc import parseObsId

async def findOffsetsAndMove(
        attcs,
        targetPosition,
        latiss=None,
        dataId=None,            # i.e. the next exposure
        butler=None,
        doMove=False,
        alwaysAcceptMove=False,
        display=None,
        timeout=100):
    

    if dataId is None:   # wait for the next event to be ingested and process it
        try:
            print("Waiting for image to arrive")
            in_oods = await latiss.atarchiver.evt_imageInOODS.next(flush=True, timeout=timeout)
        except TimeoutError:
            raise TimeoutError(f"Failed to read exposure in {timeout} seconds")

        dayObs, seqNum = parseObsId(in_oods.obsid)[-2:]
        print(f"seqNum {seqNum} arrived")

        dataId = dict(dayObs=dayObs, seqNum=seqNum)

    if False:
        exp = isrTask.run(butler.get('raw', dataId), bias=bias, defects=defects).exposure
    else:
        # We know that the raw is available, but we have to wait for the quickLookExp to be written
        maxWaitTime = 120
        dt = 0.5
        for i in range(int(maxWaitTime/dt)):
            if butler.datasetExists('quickLookExp', dataId):
                break
            await asyncio.sleep(dt)
        exp = butler.get('quickLookExp', dataId)

    centroid = findBrightestStar(exp)

    if display is not None:
        display.scale('asinh', 'zscale', Q=4)
        display.mtv(exp, title=f"{str(dataId)[1:-1]} {exp.getMetadata()['OBJECT']}")

    if centroid is None:
        raise RuntimeError("Failed to find any viable objects")

    if display is not None:
        display.dot('o', *centroid,       ctype='red', size=30)
        display.dot('o', *targetPosition, ctype='cyan', size=30)

    dx, dy = plateScale*(targetPosition - centroid)  # arcsec
    try:
        cx, cy = centroid
        peakVal = exp.image[int(cx), int(cy)]
    except Exception as e:
        print(f"Failed to get peak value ({e})")
        peakVal = None

    print(f"Offset by ({dx:.0f}, {dy:.0f}) arcsec based on seqNum {dataId['seqNum']}")
    if doMove:
        if not alwaysAcceptMove:
            reply = input(f"Do you want to slew by {dx:.1f} {dy:.1f}? [y]")
            if not reply in ("y", ""):
                raise RuntimeError("User aborted slew")
        
        await attcs.offset_xy(dx, dy, persistent=True)

    return exp, dx, dy, peakVal

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

if False:
    from lsst.atmospec.processStar import ProcessStarTask

    ProcessStarTaskConfig = ProcessStarTask.ConfigClass()
    ProcessStarTaskConfig.mainSourceFindingMethod = 'BRIGHTEST'
    processStarTask = ProcessStarTask(config=ProcessStarTaskConfig)

    def findBrightestStarMFL(exp):
        return processStarTask.findMainSource(exp)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def findBrightestStarRHL(exp, minArea=100, maxRadialOffset=1500):
    import lsst.afw.detection as afwDetect
    import lsst.afw.image as afwImage
    import lsst.afw.math as afwMath

    cexp = exp.clone()

    sigma = 4

    ksize = 1 + 4*int(sigma + 1)
    gauss1d = afwMath.GaussianFunction1D(sigma)
    kernel = afwMath.SeparableKernel(ksize, ksize, gauss1d, gauss1d)

    convolvedImage = cexp.maskedImage.Factory(cexp.maskedImage.getBBox())
    afwMath.convolve(convolvedImage, cexp.maskedImage, kernel)
    bbox = geom.BoxI(geom.PointI(ksize//2, ksize//2), geom.PointI(cexp.getWidth() - ksize//2 - 1, cexp.getHeight() - ksize//2 - 1))
    tmp = cexp.maskedImage[bbox]
    cexp.image *= 0
    tmp[bbox, afwImage.PARENT] = convolvedImage[bbox]

    del convolvedImage; del tmp

    if False:
        defectBBoxes = [
            geom.BoxI(geom.PointI(548, 3562), geom.PointI(642, 3999)),
            geom.BoxI(geom.PointI(474, 3959), geom.PointI(1056, 3999)),
            geom.BoxI(geom.PointI(500, 0),    geom.PointI(680, 40)),
        ]
        for bbox in defectBBoxes:
            cexp.maskedImage[bbox] = 0

    threshold = 1000
    feet = afwDetect.FootprintSet(cexp.maskedImage, afwDetect.Threshold(threshold), "DETECTED").getFootprints()

    maxVal = None
    centroid = None
    for foot in feet:
        peak = foot.peaks[0]
        
        if minArea > 0 and foot.getArea() < minArea:
            continue
            
        x, y = peak.getCentroid()
        if np.hypot(x - 2036, y - 2000) > maxRadialOffset:
            continue

        if maxVal is None or peak.getPeakValue() > maxVal:
            maxVal = peak.getPeakValue()
            centroid = peak.getCentroid()
            
    return centroid

findBrightestStar = findBrightestStarRHL
