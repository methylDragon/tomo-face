Data Structure Overview
=======================

Animation Directory Structure
#############################
`TomoAnimations` contains a :class:`~TomoAnimationLib.TomoAnimationLib()` class
that is able to parse a given path to an animation directory to automatically
populate path and frame libraries for animations to be played from.

This provides a code-less interface to add on to the available animations that
can be played using the :class:`~TomoFACE.TomoFACE()`. Which helps facilitate
work with artists.

Structure
*********
An example directory structure is shown as such, you can denote as many
animations as you wish!

Example directory::

  └── animation_directory_path
      ├── animation_name_1
      │   ├── transition
      │   │   ├── 01.png
      │   │   ├── 02.png
      │   │   └── 03.png
      │   └── idle
      │       ├── 01.png
      │       ├── 02.png
      │       ├── 03.png
      │       ├── ...
      │       └── frames
      ├── animation_name_2
      │   ├── transition
      │   │   ├── 01.png
      │   │   ├── 02.png
      │   │   └── 03.png
      │   └── idle
      │       ├── 01.png
      │       ├── 02.png
      │       ├── 03.png
      │       ├── ...
      │       └── frames
      ...

Ordering Frames
***************
.. warning::
  Frame numbers are assigned based off of alphanumberic order!

  As a result, it is heavily advised to name frames:

  - 01.png
  - 02.png
  - 03.png
  - ...

  Or 001.png, 002.png, 003.png, etc. depending on your needs.

  **IT IS NOT RECOMMENDED TO NAME FRAMES**:

  - 1.png
  - 2.png
  - 3.png
  - ...

  As this will cause issues when there are more than 10 frames, since 1 and 10
  will be played first before 2, which is an issue that is hard to debug unless
  you know to look for it. (And has noting to do with the code!)

  But honestly, it is up to you do decide on what naming conventions you want
  to you for your frames. All that matters is that they are sorted
  alphanumerically correctly, and it is intuitive to see what frame number each
  frame corresponds to.

Valid Image Types
*****************
The valid image types are `.gif`, `.jpg`, `.png`.

Animation Names
***************
In this case, each folder (e.g. `animation_name_1`) denotes the name of the
animation that that folder describes!

In so doing, if you wanted to grab the `animation_name_1` animation, you would
grab it using the name: `animation_name_1`.

Subanimations: Idle and Transition
**********************************
Furthermore, each animation is broken up into two subanimations:

  - Transition
  - Idle

When an animation is played, it will first play its transition frames once,
and then loop its idle frames from then on.

If you do not want an animation to play its transition you can:

  - Include **no** transition frames in the directory.
  - Configure the :class:`~TomoAnimation.TomoAnimation()` object to skip playing
    any loaded transition frames by passing in the `skip_transition` parameter
    on instantiation or :class:`~TomoAnimation.TomoAnimation.update()`.

Optional Playback File (frames)
*******************************
The frames file, which denotes a custom `playback list` is optional!

If you leave it blank or omit it, the animation frames will played
**sequentially in alphanumeric order**.

Playback Lists
##############

Description
***********
A playback list is a list of tuples of (frame_index, times_to_repeat)
which governs how a particular animation is played.

It can be defined by a playback file that is parsed using
:meth:`~TomoAnimationLib.TomoAnimationLib._generate_playback_list()`.

If a playback file is not denoted, then a default playback list is generated
that causes animation frames to be played sequentially in alphanumeric order.

.. note::
  **Playback Files**

  A playback file is any text file that denotes a sequence of frames
  to be played per loop, where each frame is delimited by newlines,
  and each frame has an optional number of times to repeat that frame.

  By default your playback file should be called `frames`.

Example
*******

The following playback file (with " " as delimiter):
    |  1 1
    |  2 2
    |  3 3

Would result in playback list: `[(1, 1), (2, 2), (3,3)]`, causing
the following to play in order per loop:

- Frame 1 to be played once
- Frame 2 to be played twice
- Frame 3 to be played thrice

Optionally, if `default_repeats` is set to 1 in the parser,
then the playback list can be written as:

    |  1
    |  2 2
    |  3 3

Resulting in playback list: `[(1, 1), (2, 2), (3,3)]`

Furthermore, playback does not need to go in order!
    |  1
    |  3 2
    |  1
    |  2 2

Would result in playback list: `[(1, 1), (3, 2), (1, 1) , (2, 2)]`
Causing the following to play in order per loop:

- Frame 1 to be played once
- Frame 3 to be played twice
- Frame 1 to be played once
- Frame 2 to be played twice

Frame Numbers
*************
If the directory had frames 01.png, 02.png, 03.png, then:

  - Frame number 1 would be 01.png
  - Frame number 2 would be 02.png
  - Frame number 2 would be 03.png

This is because 01, 02, and 03 would be sorted in that order!

Gotcha: Specifying Frame Numbers
********************************
.. warning::
  When specifying playback lists, remember that the first element on each line
  is the **frame number**. You must only specify frame numbers!

  Do **not** specify the name of the frame!

Animation Libraries
###################
The way animations ar emanaged are through the use of dictionaries called
animation libraries.

(Sorry for the confusing nomenclature! But I figured this was more in line with
the animation side of things, less so the code side of things.)

Dictionary Structure
********************
The generic animation library used by
:class:`~TomoAnimationLib.TomoAnimationLib()` is denoted as follows::

  {'animation_name_1': {'transition': {'frames': [],
                                       'playback': []},
                        'idle': {'frames': [],
                                 'playback': []},
                        'animation_path': ""},
   'animation_name_2': {'transition': {'frames': [],
                                       'playback': []},
                        'idle': {'frames': [],
                                 'playback': []},
                        'animation_path': ""},
   ...
  }

Each animation is given its own dictionary **keyed by name**, and within each
of those, notice that there are subanimation dictionaries `transition` and
`idle` for the subanimations.

Each subanimation dictionary contains `frames` and `playback`
elements.

- `frames`: Refers to the individual frame images that make up a subanimation
- `playback`: Refers to the playback list for that subanimation
- `animation_path`: Refers to the path of the animation

Path and Frame Dictionaries
***************************
Each :class:`~TomoAnimationLib.TomoAnimationLib()` instance will contain
:attr:`~TomoAnimationLib.TomoAnimationLib.animation_path_lib` and
:attr:`~TomoAnimationLib.TomoAnimationLib.animation_frame_lib`
dictionaries.

Each of these dictionaries are structured identically (with the small caveat
that the `playback` element is a string for the
:attr:`~TomoAnimationLib.TomoAnimationLib.animation_path_lib`), with the
only other difference being what is **contained** within them.

- The :attr:`~TomoAnimationLib.TomoAnimationLib.animation_path_lib`
  dictionary will contain paths to the images and playback files.

- The :attr:`~TomoAnimationLib.TomoAnimationLib.animation_frames_lib`
  dictionary will contain the loaded images and parsed playback lists.

.. note::
  Additionally, it should be noted that generally, the
  :attr:`~TomoAnimationLib.TomoAnimationLib.animation_path_lib` will come
  in fully loaded on init.

  But the :attr:`~TomoAnimationLib.TomoAnimationLib.animation_frames_lib`
  might fill up over time or get emptied as animations get loaded and unloaded
  for performance and memory optimisation.

  (This is because :class:`~TomoAnimationLib.TomoAnimationLib()`
  implements lazy initialisation and some other optimisations!)

Animation Info Dictionaries
###########################
Animation info dictionaries are used to track run-time information about
animations, normally used for debug or display purposes.

Structure::

  {'animation_name': "-",
   'frame': -1,
   'frame_repeats': -1,
   'frame_repeat_index': -1,
   'state': -1}

Notice that the elements are initialised as `-1`.

Its elements are:

  - `animation_name`: The name of the animation being played.
  - `frame`: The frame number.
  - `frame_repeats`: The number of times to repeat the current frame.
  - `frame_repeat_index`: The number of times the frame has been repeated for
    this play of the frame
  - `state`: The animation state.

    - `-1` for uninitialised
    - `0` for transition
    - `1` for idle

.. warning::
  **Frame Index Woes**

  Note that the frame index specified in `frame` is **not** the index of the
  frame in the subanimation's frame list.

  It is instead the number of the frame when the subanimation's directory is
  sorted alphanumerically.

  So, if the directory had frames 01.png, 02.png, 03.png, then frame number 1
  would be 01.png.
