"""
Author: github.com/methylDragon

████████╗ ██████╗ ███╗   ███╗ ██████╗ ██╗
╚══██╔══╝██╔═══██╗████╗ ████║██╔═══██╗██║
   ██║   ██║   ██║██╔████╔██║██║   ██║██║
   ██║   ██║   ██║██║╚██╔╝██║██║   ██║╚═╝
   ██║   ╚██████╔╝██║ ╚═╝ ██║╚██████╔╝██╗
   ╚═╝    ╚═════╝ ╚═╝     ╚═╝ ╚═════╝ ╚═╝

      - Making Devices Friendlier -

[TOMOFACE-AnimationLib: Animation Library Submodule]

Features:
- Importing, loading, processing, and generating animations from an animation
  directory
    - With sanity checks!
- On-demand/lazy initialisation
- Animation generation
- Image optimisation and scaling
"""

from TomoAnimation import TomoAnimation

import logging
import pygame
import os

# Init logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TomoAnimationLib():
    """
    TOMOFACE module for importing, loading, and generating animations from an
    animation directory

    Notes
    -----
    Animations consist of transition and idle frames.

    On animation change, transition frames will play, and then idle frames
    will loop.

    Attributes
    ----------
    animation_frame_lib : dict
        Loaded animation frames and playback lists.
    animation_path_lib : dict
        Paths to animation frames and playback lists.
    animation_path : str
        Path to overall animation directory.
    display : pygame.Display, optional
        Pygame Display object to target animations towards.

    Processing Methods
    ------------------
    aspect_scale(img, rescale_tuple)
        Get scaled image dimensions while remaining aspect ratio.
    load_images(img_path_list, rescale_tuple=None, stretch=False)
        Compute and load rescaled images as pygame surfaces.
    set_display(display)
        Set pygame display object to optimise images towards.

    Sanity Check Methods
    --------------------
    is_image_file(filename)
        Check if a given file is a valid image file.
    is_valid_animation(path)
        Check if a given path is a valid animation directory.

    IO Methods
    ----------
    add_animations(animation_path)
        Add animations from a path to path lib without loading them.
    add_and_load_animations(animation_path, rescale_tuple=None, stretch=False)
        Load and add animations from a path.
    add_single_subanimation(name, sub_name, img_path_list, playback_list=[])
        Add a single sub-animation into path lib without loading it.
    add_and_load_single_subanimation(name, sub_name,
                                     img_path_list, playback_list=[],
                                     rescale_tuple=None, stretch=False)
        Add and load a single sub-animation.

    Animation Management Methods
    ----------------------------
    load_animation(name, rescale_tuple=None, stretch=False)
        Load an animation in the path lib into the frame lib.
    load_animations(rescale_tuple=None, stretch=False)
        Load all animations in the path lib into the frame lib.
    unload_animations()
        Unload animation frame images to clear memory.
    unload_animation(name)
        Unload a single animation's frame images to clear memory.
    remove_animations()
        Remove animations from the frame and path libraries.
    remove_animation(name)
        Remove a single animation from the frame and path libraries.
    create_animation(name, rescale_tuple=None, stretch=False,
                     default_delay=1, default_skip=1,
                     skip_transition=False, animation_info_dict=None)
        Create and configure a playable `TomoAnimation`.
    update_animation(animation,
                     rescale_tuple=None, stretch=False,
                     transition_playback=None, idle_playback=None,
                     default_delay=1, default_skip=1,
                     skip_transition=False, animation_info_dict=None,
                     reset=False)
        Update an animation while preserving its sequence and state.
    """

    def __init__(self, animation_path="", display=None):
        self.animation_frame_lib = {}
        self.animation_path_lib = {}

        self.display = None
        self.animation_path = animation_path

        if animation_path:
            self.add_animations(animation_path)

    ###########################################################################
    # Processing Methods
    ###########################################################################

    def aspect_scale(self, img, rescale_tuple):
        """
        Get scaled image dimensions while retaining aspect ratio.

        Source: http://www.pygame.org/pcr/transform_scale/
        """
        bx, by = rescale_tuple
        ix, iy = img.get_size()

        if ix > iy:
            scale_factor = bx / float(ix)
            sy = scale_factor * iy
            if sy > by:
                scale_factor = by / float(iy)
                sx = scale_factor * ix
                sy = by
            else:
                sx = bx
        else:
            scale_factor = by / float(iy)
            sx = scale_factor * ix
            if sx > bx:
                scale_factor = bx / float(ix)
                sx = bx
                sy = scale_factor * iy
            else:
                sy = by

        return int(sx), int(sy)

    def load_images(self, img_path_list, rescale_tuple=None, stretch=False):
        """Compute and load rescaled images as pygame surfaces."""
        if rescale_tuple:
            if stretch:  # Stretch images to fit display
                return [pygame.transform.smoothscale(pygame.image.load(image),
                                                     rescale_tuple)
                        for image in img_path_list]

            else:  # Otherwise, preserve aspect ratio
                return [pygame.transform.smoothscale(pygame.image.load(image),
                        self.aspect_scale(pygame.image.load(image),
                                          rescale_tuple))
                        for image in img_path_list]

        else:  # If no rescale_tuple is provided, just load images naively
            return [pygame.image.load(image) for image in img_path_list]

    def set_display(self, display):
        """Set pygame display object to optimise images towards."""
        assert type(display) == pygame.Surface, \
            "Display must be of type pygame.Surface!"

        self.display = display
        self.unload_animations()

    def _optimise_animation(self, name):
        """Optimise image format for an animation's images."""
        if self.display:
            try:
                frame_lib = self.animation_frame_lib[name]
                # Convert animation library to appropriate pixel format
                for image in frame_lib['transition']['frames']:
                    image = image.convert_alpha(self.display)

                for image in frame_lib['idle']['frames']:
                    image = image.convert_alpha(self.display)
            except Exception as e:
                logger.error("%s", e)
        else:
            logger.warning("No target display specified to optimise for!")

    def _load_animation(self, name, rescale_tuple=None, stretch=False):
        """Load an animation in the path lib into the frame lib."""
        paths = self.animation_path_lib[name]

        # Generate playback lists
        if paths['transition']['playback']:
            with open(paths['transition']['playback']) as f:
                transition_playback = self._generate_playback_list(f.read())
        else:  # If no path to playback file exists, create an empty list
            transition_playback = []

        if paths['idle']['playback']:
            with open(paths['idle']['playback']) as f:
                idle_playback = self._generate_playback_list(f.read())
        else:  # If no path to playback file exists, create an empty list
            idle_playback = []

        # Load images
        transition_frames = self.load_images(paths['transition']['frames'],
                                             rescale_tuple,
                                             stretch)

        idle_frames = self.load_images(paths['idle']['frames'],
                                       rescale_tuple,
                                       stretch)

        # Populate frame lib
        self.animation_frame_lib[name] = \
            {'transition': {'frames': transition_frames,
                            'playback': transition_playback},
             'idle': {'frames': idle_frames,
                      'playback': idle_playback},
             'animation_path': paths['animation_path']}

        self._optimise_animation(name)

    ###########################################################################
    # Sanity Check Methods
    ###########################################################################

    def is_image_file(self, filename):
        """Check if a given file is a valid image file."""
        try:
            return any([filename.endswith(img_type)
                        for img_type in [".jpg", ".png", ".gif"]])
        except Exception:
            return False

    def is_valid_animation(self, path):
        """Check if a given path is a valid animation directory."""
        try:
            if "idle" in os.listdir(path) or "transition" in os.listdir(path):
                return True
            else:
                logger.warning("%s is not a valid animation folder!"
                               " It needs an /idle or /transition folder!",
                               path)
        except Exception:
            return False

    ###########################################################################
    # IO Methods
    ###########################################################################

    def add_animations(self, animation_path):
        """
        Add animations from a path to path lib without loading them.

        Traverses each generated animation dictionary from the given path,
        and updates the path lib.

        This initialises the animation libraries lazily to save memory!
        To avoid lazy initialisation, use add_and_load_animations()

        Loading, rescaling, and converting the animation surfaces will happen
        later when animations are used."""
        for name, paths in self._parse_animation_path(animation_path).items():
            self.animation_path_lib[name] = paths

        return self.animation_path_lib

    def add_and_load_animations(self, animation_path, rescale_tuple=None,
                                stretch=False):
        """Load and add animations from a path."""
        self.add_animations(animation_path)

        for name in self.animation_path_lib.keys():
            self._load_animation(name, rescale_tuple, stretch)

        return self.animation_path_lib, self.animation_frame_lib

    def add_single_subanimation(self, name, sub_name,
                                img_path_list, playback_list=[]):
        """Add a single sub-animation into path lib without loading it."""
        assert sub_name in ["transition", "idle"], \
            "sub_name must be \"idle\" or \"transition\"!"

        assert all(self.is_image_file(path) for path in img_path_list), \
            (
                "Paths in the given path list are not valid image paths: %s" %
                str([path for path in img_path_list
                     if not self.is_image_file(path)])
            )

        # Add animation path dict if it doesn't exist
        if name not in self.animation_path_lib:
            self.animation_path_lib[name] = {'transition': {'frames': [],
                                                            'playback': []},
                                             'idle': {'frames': [],
                                                      'playback': []},
                                             'animation_path': ""}

        self.animation_path_lib[name][sub_name].update(
            {'frames': img_path_list,
             'playack': playback_list}
        )

        return self.animation_path_lib

    def add_and_load_single_subanimation(self, name, sub_name,
                                         img_path_list, playback_list=[],
                                         rescale_tuple=None, stretch=False):
        """Add and load a single sub-animation."""
        assert sub_name in ["transition", "idle"], \
            "sub_name must be \"idle\" or \"transition\"!"

        self.add_single_animation(name, sub_name, img_path_list, playback_list)

        # Add animation frame dict if it doesn't exist
        if name not in self.animation_frame_lib:
            self.animation_frame_lib[name] = {'transition': {'frames': [],
                                                             'playback': []},
                                              'idle': {'frames': [],
                                                       'playback': []},
                                              'animation_path': ""}

        self.animation_frame_lib[name][sub_name].update(
            {'frames': self.load_images(img_path_list, rescale_tuple, stretch),
             'playback': playback_list}
        )

        return self.animation_path_lib, self.animation_frame_lib

    def _parse_animation_path(self, path, playback_file="frames"):
        """Parse all valid animation paths in a directory as a dict."""
        # Create output paths dict
        paths = {}

        # Iterate through all possible folder paths
        for folder_path in os.listdir(path):
            # Create path dict for single animation (from folders in path)
            animation_path_dict = {'transition': {'frames': [],
                                                  'playback': []},
                                   'idle': {'frames': [],
                                            'playback': []},
                                   'animation_path': ""}
            animation_path = path + "/" + folder_path

            # And only proceed if that animation's path is valid
            if self.is_valid_animation(animation_path):
                for sub_animation in ["transition", "idle"]:
                    try:
                        sub_animation_path = (animation_path + "/"
                                              + sub_animation + "/")
                        filenames = os.listdir(sub_animation_path)

                        animation_path_dict['animation_path'] = animation_path

                        # Construct sorted list of paths to valid frames
                        frames = [sub_animation_path + frame
                                  for frame in filenames
                                  if self.is_image_file(frame)]
                        frames.sort()
                        animation_path_dict[sub_animation]['frames'] = frames

                        # Add playback list path
                        if playback_file in filenames:
                            animation_path_dict[sub_animation]['playback'] \
                                = sub_animation_path + "/" + playback_file
                        else:
                            animation_path_dict[sub_animation]['playback'] = ""

                    except Exception as e:
                        logger.error("%s", e)

                paths[folder_path] = animation_path_dict

        return paths

    def _generate_playback_list(self, data, delimiter=" ", default_repeats=1):
        """
        Parse playback file and generate playback list.

        A playback file is any text file that denotes a sequence of frames
        to be played per loop, where each frame is delimited by newlines,
        and each frame has an optional number of times to repeat that frame.

        A playback list is a list of tuples of (frame_index, times_to_repeat)
        which governs how a particular animation is played.

        Example
        -------
        The following playback file (with " " as delimiter):
        1 1
        2 2
        3 3

        Would result in playback list: [(1, 1), (2, 2), (3,3)]
        Causing the following to play in order per loop:
        - Frame 1 to be played once
        - Frame 2 to be played twice
        - Frame 3 to be played thrice

        Optionally, if default_repeats is set to 1, then the playback list can
        be written as:
        1
        2 2
        3 3

        Resulting in playback list: [(1, 1), (2, 2), (3,3)]

        Furthermore, playback does not need to go in order!
        1
        3 2
        1
        2 2

        Would result in playback list: [(1, 1), (3, 2), (1, 1) , (2, 2)]
        Causing the following to play in order per loop:
        - Frame 1 to be played once
        - Frame 3 to be played twice
        - Frame 1 to be played once
        - Frame 2 to be played twice
        """
        if len(data) == 0:
            return []

            playback_list = data.strip().split("\n")
            output = []

            for row, frame in enumerate(playback_list, 1):
                split_frame = tuple(
                    [int(x) for x in frame.strip().split(delimiter)]
                )

                assert len(split_frame) <= 2, "Frame %d is of invalid form!" \
                    % (row)

                if len(split_frame) == 1:
                    output.append((split_frame[0], default_repeats))
                    if len(split_frame) == 2:
                        output.append(split_frame)

                        return output

    ###########################################################################
    # Animation Management Methods
    ###########################################################################

    def load_animation(self, name, rescale_tuple=None, stretch=False):
        """Load an animation in the path lib into the frame lib."""
        assert name in self.animation_path_lib, "Animation does not exist!"

        self._load_animation(name, rescale_tuple, stretch)

    def load_animations(self, rescale_tuple=None, stretch=False):
        """Load all animations in the path lib into the frame lib."""
        for name in self.animation_path_lib:
            self._load_animation(name, rescale_tuple=None, stretch=False)

    def unload_animations(self):
        """Unload animation frame images to clear memory."""
        self.animation_frame_lib = {}

    def unload_animation(self, name):
        """Unload a single animation's frame images to clear memory."""
        try:
            self.animation_frame_lib.pop(name)
        except Exception:
            pass

    def remove_animations(self):
        """Remove animations from the frame and path libraries."""
        self.animation_frame_lib = {}
        self.animation_path_lib = {}

    def remove_animation(self, name):
        """Remove a single animation from the frame and path libraries."""
        try:
            self.animation_path_lib.pop(name)
            self.animation_frame_lib.pop(name)
        except Exception:
            pass

    def create_animation(self, name, rescale_tuple=None, stretch=False,
                         default_delay=1, default_skip=1,
                         skip_transition=False, animation_info_dict=None):
        """Create and configure a playable `TomoAnimation`."""
        try:
            # If animation has not been initialised (from lazy initialisation)
            # Or the animation needs to be scaled, reload it
            if name not in self.animation_frame_lib or rescale_tuple:
                self._load_animation(name, rescale_tuple, stretch)

            return TomoAnimation(self.animation_frame_lib[name],
                                 name,
                                 default_delay=default_delay,
                                 default_skip=default_skip,
                                 skip_transition=skip_transition,
                                 animation_info_dict=animation_info_dict)
        except Exception as e:
            logger.error(e)

    def update_animation(self, animation,
                         rescale_tuple=None, stretch=False,
                         transition_playback=None, idle_playback=None,
                         default_delay=1, default_skip=1,
                         skip_transition=False, animation_info_dict=None,
                         reset=False):
        """
        Update an animation while preserving its sequence and state.

        You can update:
        - Animation source images
        - Animation playback list
        - Animation configurations
            - Default skip
            - Default delay
            - Transition skip
            - Info dict reference
        - And you can also reset the animation!

        Warnings
        --------
        This function should be called whenever any display rescaling happens
        and animations need to be rescaled in order to rescale the animations!

        It is not automatically called by this library because a default
        resolution to scale animations automatically by is not obvious for all
        possible use-cases.

        This function should only be used to give an animation scaled versions
        of its current images and/or an altered but valid playback list based
        on its original.

        If you want to completely create a new animation, you are better off
        creating a new animation instance using create_animation().

        Notes
        -----
        Animation playback sequence will only update once it completes its idle
        loop. But animation images should update immediately.

        Also, ensure new image list is at least the size of the current
        animation!
        """
        name = animation.get_name()

        # Reload frame library for specified animation if needed
        # This also checks if the animation exists within the library!
        try:
            if name not in self.animation_frame_lib or rescale_tuple:
                self._load_animation(name, rescale_tuple, stretch)
        except Exception as e:
            logger.error(e)

        # Update playback lists if called for
        if transition_playback:
            self.animation_frame_lib[name]['transition']['playback'] \
                = transition_playback
        if idle_playback:
            self.animation_frame_lib[name]['transition']['playback'] \
                = idle_playback

        animation.update(self.animation_frame_lib[name],
                         default_delay=default_delay,
                         default_skip=default_skip,
                         skip_transition=skip_transition,
                         animation_info_dict=animation_info_dict,
                         reset=reset)
