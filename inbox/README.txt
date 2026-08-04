PUT YOUR VIDEOS IN THIS FOLDER
======================================================================

Copy or drag your video files here, then run the program:

    Windows      double-click  run.cmd
    Mac / Linux  run  ./run.sh

Every video in this folder is processed. Results appear in the "output"
folder, in a subfolder named after each video.


WHICH FILES WORK
----------------------------------------------------------------------

  mp4   mkv   avi   mov   wmv   flv   webm   m4v   mpg   mpeg   ts   3gp

The video must have sound. A video with no audio track cannot be
transcribed, and the program will say so rather than producing an empty
file.


A FEW PRACTICAL NOTES
----------------------------------------------------------------------

  - Large files are fine. A 3 GB recording is read straight from disk and
    is never copied.

  - Nothing here is modified or deleted. Your original file stays exactly
    as it is.

  - The file name becomes the name of the results folder, so a name like
    "Smith_hearing_2025-07-23.mp4" is easier to find later than "VID_0042.mp4".

  - If a recording is long and you are not sure the audio is usable, test
    a short stretch of it first:

        python videoscribe.py run --start 00:12:00 --duration 00:03:00

    That takes about a minute and tells you whether the language setting
    and the sound quality are good enough before you commit to a long run.


PRIVACY
----------------------------------------------------------------------

The transcript is produced entirely on this computer. Nothing is uploaded
and no account is needed.

The optional description of what is visible on screen is different: it
sends still frames from the video to an image model over the internet. If
the footage must not leave this machine, choose "Transcript only" in the
menu.
