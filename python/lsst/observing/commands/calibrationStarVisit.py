import asyncio
import logging
import numpy as np

import lsst.observing.utils.focus
from lsst.observing.constants import (boreSight, sweetSpots)
from lsst.observing.utils.audio import playSound
from lsst.observing.utils.offsets import findOffsetsAndMove
from lsst.observing.utils.filters import changeFilterAndGrating, getFilterAndGrating

async def takeData(attcs,
                   latiss,
                   butler,
                   objectName,
                   exposures = [
                       (   'empty_1', 45, 'ronchi90lpmm'),
                       ('quadnotch1', 45,           None),
                       (      'BG40', 45,           None),
                       (     'RG610', 45,           None),
                       (      'BG40',  3,      'empty_1'),
                       (        None, 20,           None),
                       (     'RG610',  3,           None),
                       (       None,  20,           None),
                   ],
                   updateFocus=True,
                   alwaysAcceptMove=True,
                   display=None,
                   expTime0=1.0,
                   doPointingModel=False,
                   logger = None,
                   silent=False,
             ):
    """
    Slew to an object and take a set of exposures

    Parameters
    ----------
    attcs : `lsst.ts.standardscripts.auxtel.attcs.ATTCS`
        The object describing the AT's TCS
    latisss : `lsst.ts.standardscripts.auxtel.latiss.LATISS`
        The object describing the LATISS instrument
    butler : `lsst.daf.persistence.Butler`
        The butler providing access to the data
    objectName : `str`
        The object to observe. Anything attcs.slew_object() understands
    exposures : `list`
        A list of science exposures to be taken; each element is
            (filter, exposureTime, grating)
        If filter or grating is `None` use the current value.
        N.b. exposureTime is in units of expTime0
    updateFocus : `bool`
        If true, prompt for updated focus offset
    alwaysAcceptMove : `bool`
        Assume that proposed offsets are correct and proceed without user confirmation
    display : `lsst.afw.display.Display`
        An display for displaying images
    expTime0 : `float`
        All exposure times are expressed in units of expTime0
    doPointingModel : `bool`
        If true, move the object to the boresight and log the object for the pointing model
    logger : `logging.Logger`
        The logger to use to report what's going on (at level Info)
    silent : `bool`
        If true, suppress all noises

    Returns
    -------
    info : `dict`
        Translated information from the metadata. Updated form of the
        input parameter.

    Notes
    -----
    
    """
    #
    # Check that exposures list is well-formed
    #
    for i, exposure in enumerate(exposures):
        if len(exposure) != 3:
            raise RuntimeError(f"Expected 3 elements (filter, expTime, grating) in [{i}] element in exposures"
                               f" saw '{exposure}'")
        if i == 0:
            filter, expTime, grating = exposure
            if filter is None:
                raise RuntimeError("You must specify a filter for the first exposure")
            if grating is None:
                raise RuntimeError("You must specify a grating for the first exposure")
    
    #
    # Get a logger if none is provided
    #
    if logger is None:
        logger = logging.getLogger()

    # Slew to object with Parallactic compensation on;
    # we do this with neither a filter nor a grating in the beam

    if object is None:
        if doPointingModel:
            raise RuntimeError("It makes no sense to set `doPointingModel` when object is `None`")
    else:
        pa_angs = [0, -180]                 # possible values of the position angle
        for i, pa_ang in enumerate(pa_angs):
            try:
                await asyncio.gather(
                    attcs.slew_object(name=objectName, pa_ang=pa_ang, slew_timeout=240),
                    latiss.setup_atspec(grating='empty_1', filter='empty_1'),
                )
            except Exception as e:
                if i == 0:
                    print(f"Failed to go to {pa_ang} ({e}); trying {pa_angs[1]}")
                else:
                    raise
            else:
                print(f"pa = {pa_ang}")
                break

        logger.info(f"At {objectName}")
        if not silent:
            playSound()

    # We are now nominally at the boresight.  We need to check this if we're updating the pointing model

    # if `doPointingModel` is true:
    # 
    # - b. take test image, determine offset to boresight
    # - c. sanity-check the computed offsets
    # - d. do x,y offset to center object at boresight

    if doPointingModel:
        targetPosition = boreSight
        # Iterate to put star on boresight
        success=False
        for i in range(5):

             retvals = await asyncio.gather(
                 findOffsetsAndMove(attcs, targetPosition, latiss, dataId=None, butler=butler,
                                    doMove=True, alwaysAcceptMove=alwaysAcceptMove),
                 latiss.take_object(exptime=expTime0, n=1),
             )
             exp, dx, dy, peakVal = retvals[0]
             print('Calculated offsets [dx,dy] are [{},{}]'.format(dx,dy))

             dr=np.sqrt(dx**2.0+dy**2.0)
             print('Current radial pointing error is {}'.format(dr))
             if dr < 2.0:
                  success=True
                  break
        
        if success:
             print('Achieved Centering accuracy')
        else:
             print('Failed to center star on boresight')
             return
        
        if not silent:
            playSound()

        # Check that we're at the boresight
        await latiss.take_object(exptime=expTime0, n=1)

        logger.info(f"Moved {objectName} to boresight")
        if not silent:
            playSound()
        #
        # Update pointing model
        #
        print('Adding datapoint to pointing model')
        await attcs.add_point_data()

        return # this skips the acquisition below
    #
    # Done with pointing model.
    # 
    # Offset to sweet spot with grating correction (so the star will be in the wrong place as we don't have
    # a grating in)

    # f. take a test exposure and check flux levels, determine best exptime for `grating`
    #
    if len(exposures) == 0:
        return

    filter, _, grating = exposures[0]       # we checked earlier that these exist

    targetPosition = sweetSpots[grating]

    retvals = await asyncio.gather(
        findOffsetsAndMove(attcs, targetPosition, latiss, dataId=None, butler=butler, 
                           doMove=True, alwaysAcceptMove=alwaysAcceptMove, display=display),
        latiss.take_object(exptime=expTime0, n=1, filter=filter, grating=grating),
    )
    exp, dx, dy, peakVal = retvals[0]

    logger.info(f"Checked flux for {objectName}: peak value = {peakVal:.0f}")
    if not silent:
        playSound()
    #
    # N.b. we could use the peakVal to update expTime0
    #
    pass

    if updateFocus:
        # Run focus sweep and measure desired focus offset
        while True:
            reply = input("What is the best focus offset for the current configuration (mm)? ")
            try:
                focus_offset = float(reply)
            except Exception as e:
                print(f"Error ({e}).  Please try again:")
            else:
                break

        if False:
            attcs.athexapod.evt_positionUpdate.flush()
        else:
            await asyncio.sleep(5)

        await attcs.ataos.cmd_applyFocusOffset.set_start(offset=focus_offset) 
        await attcs.athexapod.evt_positionUpdate.next(flush=False, timeout=attcs.long_timeout)
        
        lsst.observing.utils.focus.myFocusOffset = focus_offset

        logger.info("Adjusted focus")
        if not silent:
            playSound()

    # At this point the grating/filter are set to those in exposures[0]
    # 
    # Ready for science!

    currentFilter, currentGrating = await getFilterAndGrating(latiss) # how long does this take? Caching...

    nexp = len(exposures)
    for i, (filter, expTime, grating) in enumerate(exposures):
        await changeFilterAndGrating(attcs, latiss, filter=filter, grating=grating)
        await latiss.take_object(exptime=expTime*expTime0, n=1)

        if filter != None:
            currentFilter = filter
        if grating != None:
            currentGrating = grating

        logger.info(f"Took {expTime*expTime0:6.1f}s exposure ({currentFilter}/{currentGrating})")
        if not silent:
            playSound('ding' if i < nexp - 1 else "gong")


    return expTime0
