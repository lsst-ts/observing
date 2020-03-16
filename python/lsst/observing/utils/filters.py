import asyncio
from lsst.observing.constants import dFocusDthickness, glassThicknesses, plateScale, gratingOffsets

__all__ = ["getFilterAndGrating", "changeFilterAndGrating"]


async def getFilterAndGrating(latiss):
    """Return the current filter and grating"""
    filter_pos = await latiss.atspectrograph.evt_reportedFilterPosition.aget()
    grating_pos = await latiss.atspectrograph.evt_reportedDisperserPosition.aget()

    return filter_pos.name, grating_pos.name


async def changeFilterAndGrating(attcs, latiss, filter=None, grating=None):
    """Insert filter and/or grating leaving the stars at the same place and focus"""

    currentFilter, currentGrating = await getFilterAndGrating(latiss)
    if filter is None:
        filter = currentFilter
    if grating is None:
        grating = currentGrating

    focus_offset = dFocusDthickness*((glassThicknesses[filter] - glassThicknesses[currentFilter]) +
                                     (glassThicknesses[grating] - glassThicknesses[currentGrating]))

    dx, dy = plateScale*(gratingOffsets[grating] - gratingOffsets[currentGrating])

    attcs.athexapod.evt_positionUpdate.flush()
    print(f'Applying focus offset of {focus_offset} for filter {filter} and grating {grating}')
    await attcs.ataos.cmd_offset.set_start(z=focus_offset)

    if False:
        evt_positionUpdate = attcs.athexapod.evt_positionUpdate.next(flush=False, timeout=attcs.long_timeout)
    else:
        evt_positionUpdate = asyncio.sleep(5)

    await asyncio.gather(
        evt_positionUpdate,
        latiss.setup_atspec(filter=filter, grating=grating),
        attcs.offset_xy(dx, dy, persistent=True),
    )

    return filter, grating
