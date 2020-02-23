__all__ = ["parseObsId"]


def parseObsId(obsId):
    """Split an obsId into its constituent parts
    
    E.g.
        parseObsId('AT_O_20200219_000212')
    """
    source, controller, dayObs, seqNum = obsId.split('_')
    dayObs = f"{dayObs[0:4]}-{dayObs[4:6]}-{dayObs[6:8]}"
    seqNum = int(seqNum)
    
    return source, controller, dayObs, seqNum
