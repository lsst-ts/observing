__all__ = ["myFocusOffset"]
#
# focus offsets aren't sticky, so we have to maintain the offset in software.  Sigh
#
try:
    myFocusOffset
except NameError:
    myFocusOffset = 0
