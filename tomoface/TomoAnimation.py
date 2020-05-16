"""
Author: github.com/methylDragon

████████╗ ██████╗ ███╗   ███╗ ██████╗ ██╗
╚══██╔══╝██╔═══██╗████╗ ████║██╔═══██╗██║
   ██║   ██║   ██║██╔████╔██║██║   ██║██║
   ██║   ██║   ██║██║╚██╔╝██║██║   ██║╚═╝
   ██║   ╚██████╔╝██║ ╚═╝ ██║╚██████╔╝██╗
   ╚═╝    ╚═════╝ ╚═╝     ╚═╝ ╚═════╝ ╚═╝

      - Making Devices Friendlier -

[TOMOFACE-Animation: Animation Submodule]

A manageable sequence of frames and a playback list that handles on-demand
'lossless' image scaling.

Features:
- Frame sequence management (reset, skips, advances)
- Interface for image properties
- On-demand image scaling that preserves image quality over repeated scales
- Animation real-time information tracking
"""

# Get height/width

import pygame
import logging

# Init logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TomoAnimation():
    def __init__(self,
                 animation_dict,
                 default_delay=1,
                 default_skip=1,
                 skip_transition=False,
                 animation_info_dict=None):
        """
        Animation dict is of structure:

        {'transition': {'frames': [],
                        'playback': []},
         'idle': {'frames': [],
                  'playback': []},
         'animation_path': ""}
        """

        # Init output frame variables
        self.frame = pygame.Surface((0, 0))  # Current output frame
        self._frame_prior = pygame.Surface((0, 0))  # Pre-processed frame

        # Init animation detail vars
        self.animation_name = animation_dict['animation_path']

        self.idle_frames = animation_dict['idle']['frames']
        self.transition_frames = animation_dict['transition']['frames']

        self.idle_playback = animation_dict['idle']['playback']
        self.transition_playback = animation_dict['transition']['playback']

        # Init configuration vars
        self.default_delay = default_delay
        self.default_skip = default_skip
        self.skip_transition = skip_transition

        # Init info tracking var
        self.animation_info_dict = animation_info_dict

        # If no playback list is passed, generate one
        if len(self.transition_playback) == 0:
            self.transition_playback = [
                (x, self.default_delay)
                for x in range(len(self.transition_frames))
            ]

        if len(self.idle_playback) == 0:
            self.idle_playback = [
                (x, self.default_delay) for x in range(len(self.idle_frames))
            ]

        # Generate animation sequence iterator and running tracking vars
        self.sequence = self._sequence()
        self.last_scale = None

    def __next__(self):
        return self.advance()

    def __iter__(self):
        return self.sequence

    def update(self, animation_dict, default_delay=None,
               skip_transition=None, animation_info_dict=None,
               reset=False):
        """Update animation attributes."""
        self.name = animation_dict['animation_path']
        self.idle_frames = animation_dict['idle']['frames']
        self.transition_frames = animation_dict['transition']['frames']

        self.idle_playback = animation_dict['idle']['playback']
        self.transition_playback = animation_dict['transition']['playback']

        if default_delay:
            self.default_delay = default_delay
        if skip_transition:
            self.skip_transition = skip_transition
        if animation_info_dict:
            self.animation_info_dict = animation_info_dict

        if reset:
            self.reset_animation()

    def reset(self, skip_transition=None):
        """Reset animation sequence, and play from start."""
        if skip_transition:
            self.skip_transition = skip_transition

        self.sequence = self._sequence()

    def advance(self, skip=None,
                rescale_tuple=None, inplace=False, smooth=True):
        """Advance animation sequence, with optional scaling."""
        if not skip:
            skip = self.default_skip

        for skips in range(skip):
            self._frame_prior = next(self.sequence)

        self.frame = self._frame_prior
        self.last_scale = rescale_tuple

        return self.get_frame(rescale_tuple,
                              inplace=inplace,
                              smooth=smooth)

    def scale_frame(self, frame, rescale_tuple, smooth=True):
        """Scale a frame."""
        if smooth:
            return pygame.transform.smoothscale(self._frame_prior,
                                                rescale_tuple)
        else:
            return pygame.transform.scale(self._frame_prior,
                                          rescale_tuple)

    def get_frame(self, rescale_tuple=None, inplace=False, smooth=True):
        """Get current frame, with optional scaling."""
        if rescale_tuple:
            if self.last_scale == rescale_tuple:
                return self.frame

            output = self.scale_frame(self._frame_prior, rescale_tuple, smooth)

            if inplace:
                self.last_scale = rescale_tuple
                self.frame = output

            return output
        else:
            return self.frame

    # Getters
    def get_frame_size(self):
        return self.frame.get_size()

    def get_frame_height(self):
        return self.frame.get_height()

    def get_frame_width(self):
        return self.frame.get_width()

    def _sequence(self):
        """Dynamically generated custom animation iterable sequence."""
        # Play transition
        if not self.skip_transition:
            for frame_index, frame_delay in self.transition_playback:
                try:
                    if self.animation_info_dict:
                        try:
                            self.animation_info_dict['animation_name'] \
                                = self.animation_name
                        except Exception:
                            self.animation_info_dict['animation_name'] \
                                = "ERROR"

                        self.animation_info_dict.update(
                            {
                                'state': 0,
                                'frame_delay': frame_delay,
                                'frame': frame_index + 1
                             }
                        )

                    for i in range(frame_delay):
                        if self.animation_info_dict:
                            self.animation_info_dict['frame_delay_index'] \
                                = i + 1

                        yield self.transition_frames[frame_index]

                except Exception as e:
                    if self.animation_info_dict:
                        self.animation_info_dict['frame_delay_index'] = -1

                    logger.error(
                        "%s | Transition frame %d for %s does not exist!"
                        % (e, frame_index, self.animation_name)
                    )

                    yield None

        # Play idle on loop
        while True:
            for frame_index, frame_delay in self.idle_playback:
                try:
                    if self.animation_info_dict:
                        try:
                            if self.animation_name:
                                self.animation_info_dict['animation_name'] \
                                    = self.animation_name
                            else:
                                self.animation_info_dict['animation_name'] \
                                    = self.animation_dict['animation_name']
                        except Exception:
                            self.animation_info_dict['animation_name'] \
                                = "ERROR"

                        self.animation_info_dict.update(
                            {
                                'state': 0,
                                'frame_delay': frame_delay,
                                'frame': frame_index + 1
                             }
                        )

                    for i in range(frame_delay):
                        if self.animation_info_dict:
                            self.animation_info_dict['frame_delay_index'] \
                                = i + 1

                        yield self.idle_frames[frame_index]

                except Exception as e:
                    if self.animation_info_dict:
                        self.animation_info_dict['frame_delay_index'] = -1

                    logger.error(
                        "%s | Idle frame %d for %s does not exist!"
                        % (e, frame_index, self.animation_name)
                    )

                    yield None
