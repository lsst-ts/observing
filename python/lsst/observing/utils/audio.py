import os
#from IPython.display import Audio, display
import IPython.display as ipd

__all__ = ["playSound"]

soundDir = os.path.join(os.environ["OBSERVING_DIR"], "resources", "sounds")

def playSound(sound=None):
    f"""Play a sound, either a name mapping to a file in in {soundDir} or a URL
    
    If sound is "list", list your options
    """
    knownSounds = dict(bell = "DeskBell.wav",
                       gong = "chinese-gong.wav",
                       ding = "ding.wav",
                  )

    if sound is None:
        sound = "bell"

    if sound is "list":
        print("Registered sounds in {soundDir}:")
        for k, v in knownSounds.items():
            print(f"\t{k:20s} {v}")
        print("or use a URL")
        return
    
    if sound in knownSounds:
        snd = os.path.join(os.path.expanduser(soundDir), knownSounds[sound])
    else:
        snd = sound

    ipd.display(ipd.Audio(snd, autoplay=True))
    ipd.set_matplotlib_close(close=True)
    
if __name__ == "__main__":
    playSound(None)
