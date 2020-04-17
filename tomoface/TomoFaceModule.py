"""
Author: github.com/methylDragon

████████╗ ██████╗ ███╗   ███╗ ██████╗ ██╗
╚══██╔══╝██╔═══██╗████╗ ████║██╔═══██╗██║
   ██║   ██║   ██║██╔████╔██║██║   ██║██║
   ██║   ██║   ██║██║╚██╔╝██║██║   ██║╚═╝
   ██║   ╚██████╔╝██║ ╚═╝ ██║╚██████╔╝██╗
   ╚═╝    ╚═════╝ ╚═╝     ╚═╝ ╚═════╝ ╚═╝

      - Making Devices Friendlier -

[TOMOFACE: Face Animation Character Engine]

Features:
- TOMO animation engine

Runs two threads:
- _animation_advance_thread thread
- _display_update_thread thread
"""

# Import subpackages
try:
    from .pid import PIDController
    from .utils import add_animations, add_single_animation, \
                       parse_animation_path, load_images
except:
    pass

from threading import Thread, Lock

import pkg_resources
import time
import math
import pygame
import random
import sys
import os

# TODO:
# Separate PID to its own thread
# WRITE SET POSITION EQUATION

# Remove blink when setting animation by setting last blink time forward in the future!

# Potentially subclass animation module?
# ROTATION
# Rename PID module
# Figure out last animation name

# TODO:
# Note that eyes and mouth image resolutions per animation must be identical

# frequency = 0.2
# print(math.sin(pygame.time.get_ticks() / 1000 * 2 * math.pi * frequency))

## VARIABLE NAMING CONVENTION ## (There are a lot of x and y variables...)
# x_{NAME} represents a COORDINATE for NAME the x-axis
# y_{NAME} represents a COORDINATE for NAME in the y-axis
# {NAME}_x represents an AMOUNT or DIMENSION for NAME in the x-axis


class TomoFaceModule():
    def __init__(self, init_pygame=True, animation_path=pkg_resources.resource_filename(__name__, 'media/tomo_animations'),
                 motion_fps=60, animation_fps=24, blink_fps=40,
                 mouth_offset=(0, 0),
                 x_pid={'p': 0.025, 'i': 0.005, 'd': 0.0},
                 y_pid={'p': 0.025, 'i': 0.005, 'd': 0.0},
                 background_colour=(255, 255, 255),
                 default_eyes_animation_timeout=2000,
                 default_mouth_animation_timeout=2000,
                 position_timeout=1000,
                 blink_animation_name="blink", enable_blink=True,
                 eyes_neutral_animation_name="neutral_eyes",
                 mouth_neutral_animation_name="neutral_mouth",
                 start_display=True,
                 display_mode=0,
                 no_mouth=False,
                 overlay_image=False, overlay_image_offset=(0,0),
                 resolution=None,
                 surface_mode=False,
                 y_padding=0.05,
                 squash_window=0.15, squash_amount_x=0.5, squash_amount_y=0.5,
                 bob_amount=0, bob_frequency=0.2,
                 skip_neutral_transition=False,
                 performance_mode=False,
                 stretch_face=False):

        self.lock = Lock()

        self.pygame_running = False
        self.stop_pygame = False
        self.resolution = resolution
        self.display_mode=0
        # TODO: Organise these
        self.stretch_face = stretch_face
        self.y_padding = y_padding
        self.squash_window = squash_window
        self.squash_amount_x = squash_amount_x
        self.squash_amount_y = squash_amount_y
        self.bob_amount = bob_amount
        self.bob_frequency = bob_frequency
        self.skip_neutral_transition = skip_neutral_transition

        self.performance_mode = performance_mode

        # Init pygame
        if init_pygame:
            self.init_pygame()

        # Init PID controllers
        self.x_pid = PIDController(x_pid['p'], x_pid['i'], x_pid['d'])
        self.y_pid = PIDController(y_pid['p'], y_pid['i'], y_pid['d'])

        ## Init colours
        self.background_colour = background_colour

        ## Init mouth offset
        self.mouth_offset = mouth_offset
        self.no_mouth = no_mouth

        ## Init last command times
        self.last_position_time = 0
        self.last_eyes_animation_time = 0
        self.last_mouth_animation_time = 0
        self.last_blink_time = 0

        ## Init last animation timeouts
        self.eyes_animation_timeout = 0
        self.mouth_animation_timeout = 0

        ## Init resize buffer and timeout
        self.resize_buffer = None
        self.last_resize_time = 0

        ## Init default timeouts
        self.default_eyes_animation_timeout = default_eyes_animation_timeout
        self.default_mouth_animation_timeout = default_mouth_animation_timeout
        self.position_timeout = position_timeout

        ## FPS Params
        self.motion_fps = motion_fps
        self.animation_fps = animation_fps
        self.blink_fps = blink_fps

        ## Overlay Image Params
        self.overlay_image_flag = overlay_image
        self.overlay_image_offset = overlay_image_offset
        self.overlay_image = pygame.Surface((self.display_width, self.display_height))
        self.surface_mode = surface_mode
        self.output_surface = pygame.Surface((self.display_width, self.display_height))

        ## Init animation library
        self.animation_lib = {}
        self.animation_path_lib = {}
        self.animation_path = animation_path

        ## Init starting animations
        if self.animation_path != "":
            self.add_animations(self.animation_path)


        # All changes are made to prior, before being processed to the final one
        # This is to ensure there is always a lossless image being used
        self.eyes_display_img = None
        self.eyes_display_img_prior = None
        self.eyes_animation = None
        self.eyes_animation_name = None
        self.eyes_animation_info_dict = {'animation_name': "-",
                                        'frame': -1,
                                        'frame_delay': -1,
                                        'frame_delay_index': -1,
                                        'state': -1}

        self.mouth_display_img = None
        self.mouth_display_img_prior = None
        self.mouth_animation = None
        self.mouth_animation_name = None
        self.mouth_animation_info_dict = {'animation_name': "-",
                                          'frame': -1,
                                          'frame_delay': -1,
                                          'frame_delay_index': -1,
                                          'state': -1}

        self.blink_animation = None

        self.eyes_height = None
        self.eyes_width = None
        self.mouth_height = None
        self.mouth_width = None

        ## Init Animation Defaults
        self.enable_blink = enable_blink

        self.blink_animation_name = blink_animation_name
        self.eyes_neutral_animation_name = eyes_neutral_animation_name
        self.mouth_neutral_animation_name = mouth_neutral_animation_name

        if start_display:
            self.start_display_threads()

    def init_pygame(self):
        # Init Pygame
        pygame.display.init()

        # Init Display Parameters
        self.infoObject = pygame.display.Info()

        if self.resolution:
            self.display_width, self.display_height = self.resolution
        else:
            (self.display_width, self.display_height) = (self.infoObject.current_w, self.infoObject.current_h)
            self.resolution = (self.display_width, self.display_height)

        # Init clock
        self.clock = pygame.time.Clock()

        # Init last command times
        self.last_position_time = 0
        self.last_eyes_animation_time = 0
        self.last_mouth_animation_time = 0
        self.last_blink_time = 0

        self.pygame_running = True
        self.stop_pygame = False

    def stop_pygame(self):
        self.stop_pygame = True

    def set_background_colour(self, colour_tuple):
        self.background_colour = colour_tuple

    def load_images(self, img_path_list, rescale_tuple=None, stretch=False):
        """Compute and load rescaled images as pygame surfaces."""
        if self.pygame_running:
            if rescale_tuple is None:
                rescale_tuple = (self.resolution[0] // 2, self.resolution[1] // 2)

            return load_images(img_path_list, rescale_tuple, stretch)
        else:
            print("Pygame not started! Call init_pygame() to start!")
            return []

    def add_single_animation(self, name, sub_name,
                             img_path_list, playback_list=[]):
        """Add a single sub-animation to the animation path library."""
        add_single_animation(name, sub_name, img_path_list, playback_list,
                                   self.animation_path_lib)

    def add_animations(self, animation_path, verbose=True):
        """
        Add animation paths from a given overall path to the animation path library.

        Traverses each generated animation dictionary from the given path,
        and updates the visual path library.

        This initialises the animation lib lazily!
        To avoid lazy initialisation, use add_and_load_animations()

        Loading, rescaling, and converting the animation surfaces will happen
        later when animations are generated."""
        add_animations(animation_path, verbose, self.animation_path_lib)

    def add_and_load_single_animation(self, name, sub_name,
                                      img_path_list, playback_list=[],
                                      rescale_tuple=None):
        """Add and load a single sub-animation."""
        add_single_animation(name, sub_name, img_path_list, playback_list)

        self.animation_lib[name][sub_name] = self.load_images(img_path_list, rescale_tuple, stretch=self.stretch_face)
        self.animation_lib[name][sub_name + "_playback"] = playback_list

    def add_and_load_animations(self, animation_path, verbose=True, rescale_tuple=None):
        """Load and add animations from a given path."""
        self.add_animations(animation_path, verbose=verbose)

        for animation_name, animation_path_dict in parse_animation_path(animation_path, verbose=verbose).items():
            # Traverse each generated animation dictionary from the path
            # And mutate the overall dictionary by loading all included image paths
            for property, contents in animation_path_dict.items():
                # Skip if empty
                if len(contents) == 0:
                    continue

                # Skip if it's a playback list
                if type(contents[0]) != str:
                    continue

                # Skip also if it is the name property
                if property == "animation_name":
                    continue

                # Otherwise, replace all paths in dict with loaded surfaces
                animation_path_dict[property] = self.load_images(contents, rescale_tuple, stretch=self.stretch_face)

            # And update the visual library
            self.animation_lib[animation_name] = animation_path_dict

    def _animation_generator(self, animation_dict=None, default_delay=1, transition=[], idle=[],
                            transition_playback_list=[], idle_playback_list=[], skip_transition=False,
                            animation_info_dict=None, animation_name=""):
        """Dynamically generate custom animation."""
        # If animation dictionary is passed, load it
        if not animation_dict is None:
            transition = animation_dict.get('transition', [])
            idle = animation_dict.get('idle', [])
            transition_playback_list = animation_dict.get('transition_playback', [])
            idle_playback_list = animation_dict.get('idle_playback', [])

        # If no playback list is passed, generate one
        if len(transition_playback_list) == 0:
            transition_playback_list = [(x, default_delay) for x in range(len(transition))]

        if len(idle_playback_list) == 0:
            idle_playback_list = [(x, default_delay) for x in range(len(idle))]

        # Play transition
        if not skip_transition:
            for frame_index, frame_delay in transition_playback_list:
                try:
                    if animation_info_dict:
                        try:
                            if animation_name:
                                animation_info_dict['animation_name'] = animation_name
                            else:
                                animation_info_dict['animation_name'] = animation_dict['animation_name']
                        except Exception as e:
                            animation_info_dict['animation_name'] = "ERROR"

                        animation_info_dict['state'] = 0
                        animation_info_dict['frame_delay'] = frame_delay
                        animation_info_dict['frame'] = frame_index + 1

                    for i in range(frame_delay):
                        if animation_info_dict:
                            animation_info_dict['frame_delay_index'] = i + 1

                        yield transition[frame_index]

                except Exception as e:
                    if animation_info_dict:
                        animation_info_dict['frame_delay_index'] = -1

                    print("_animation_generator():", e)
                    print("Transition frame", frame_index,
                          "for", animation_name, "does not exist!")

                    yield None

        # Play idle on loop
        while True:
            for frame_index, frame_delay in idle_playback_list:
                try:
                    if animation_info_dict:
                        try:
                            if animation_name:
                                animation_info_dict['animation_name'] = animation_name
                            else:
                                animation_info_dict['animation_name'] = animation_dict['animation_name']
                        except:
                            animation_info_dict['animation_name'] = "ERROR"

                        animation_info_dict['state'] = 1
                        animation_info_dict['frame_delay'] = frame_delay
                        animation_info_dict['frame'] = frame_index + 1

                    for i in range(frame_delay):
                        if animation_info_dict:
                            animation_info_dict['frame_delay_index'] = i + 1

                        yield idle[frame_index]

                except Exception as e:
                    if animation_info_dict:
                        animation_info_dict['frame_delay_index'] = -1

                    print("_animation_generator():", e)
                    print("Idle frame", frame_index,
                          "for", animation_name, "does not exist!")

                    yield None

    def set_position_goal(self, x, y):
        """
        Set top left corner of eyes to an (x, y) position goal.

        The top left corner of the display is (0, 0) and coordinates are (x, y).
        """
        self.x_goal = x
        self.y_goal = y

        self.last_position_time = pygame.time.get_ticks()

    def set_offset_goal(self, x, y):
        """
        Set position goal of eyes center in an (x, y) offset from the center.

        Moving towards the right is in the +x direction.
        Moving towards the bottom is in the +y direction.
        """
        (x_center, y_center) = self.calculate_blit_for_center(self.eyes_display_img_prior)

        self.x_goal = x_center + x
        self.y_goal = y_center + y

        self.last_position_time = pygame.time.get_ticks()

    def increment_position_goal(self, x, y):
        """
        Increment current position goal of eyes in the (x, y) direction.

        Moving towards the right is in the +x direction.
        Moving towards the bottom is in the +y direction.
        """
        self.x_goal += x
        self.y_goal += y

        self.last_position_time = pygame.time.get_ticks()

    def load_animation(self, animation_name):
        animation_dict = \
            {'idle': self.load_images(
                self.animation_path_lib[animation_name]['idle'],
                stretch=self.stretch_face),
             'transition': self.load_images(
                self.animation_path_lib[animation_name]['transition'],
                stretch=self.stretch_face)}

        self.animation_lib[animation_name] = animation_dict
        self.optimise_animation(animation_name)

    def set_eyes_animation(self, animation_name, default_delay=1, timeout=None,
                           skip_transition=False, force_reset_animation=False,
                           no_blink=False):
        """Set current eye animation."""
        # If the same animation is requested,
        # and no request to replay it is made, return
        if self.eyes_animation_name == animation_name \
           and not force_reset_animation:
            return

        if not animation_name in self.animation_lib:
            try:
                self.load_animation(animation_name)
            except Exception as e:
                print("set_eyes_animation():", e)
                return

        # Verify animation exists
        if animation_name in self.animation_lib:
            self.eyes_animation = self._animation_generator(
                self.animation_lib[animation_name],
                default_delay=default_delay,
                skip_transition=skip_transition,
                animation_info_dict= self.eyes_animation_info_dict)
        else:
            # TODO: Change this to logging
            print("set_eyes_animation()")
            return

        self.eyes_animation_name = animation_name

        if timeout is None:
            self.eyes_animation_timeout = self.default_eyes_animation_timeout
        else:
            self.eyes_animation_timeout = timeout

        if no_blink:
            self.last_blink_time = pygame.time.get_ticks() + self.eyes_animation_timeout

        self.last_eyes_animation_time = pygame.time.get_ticks()

    def set_mouth_animation(self, animation_name, default_delay=1, timeout=None,
                            skip_transition=False, force_reset_animation=False,
                            no_blink=False):
        """Set current mouth animation."""
        # If the same animation is requested,
        # and no request to replay it is made, return
        if self.mouth_animation_name == animation_name \
           and not force_reset_animation:
            return

        if self.no_mouth:
            self.mouth_animation_timeout = self.eyes_animation_timeout
            return

        if not animation_name in self.animation_lib:
            try:
                self.load_animation(animation_name)
            except Exception as e:
                print("set_mouth_animation():", e)
                return

        self.mouth_animation = self._animation_generator(
            self.animation_lib[animation_name],
            default_delay=default_delay,
            skip_transition=skip_transition,
            animation_info_dict=self.mouth_animation_info_dict)

        self.mouth_animation_name = animation_name

        if timeout is None:
            self.mouth_animation_timeout = self.default_mouth_animation_timeout
        else:
            self.mouth_animation_timeout = timeout

        if no_blink:
            self.last_blink_time = pygame.time.get_ticks() + self.mouth_animation_timeout

        self.last_mouth_animation_time = pygame.time.get_ticks()

    def show_mouth(self):
        """Show mouth."""
        self.no_mouth = False

    def hide_mouth(self):
        """Hide mouth."""
        self.no_mouth = True

    def show_blink(self):
        """Enable blink."""
        self.enable_blink = True

    def hide_blink(self):
        """Disable blink."""
        self.enable_blink = False

    def optimise_animation(self, name):
        try:
            # Convert animation library to appropriate pixel format
            for image in self.animation_lib[name]['transition']:
                image = image.convert_alpha(self.display)

            for image in self.animation_lib[name]['idle']:
                image = image.convert_alpha(self.display)
        except:
            pass

    def set_blink_animation(self, name, default_delay=1):
        """Set blink animation."""
        if not name in self.animation_lib:
            try:
                animation_dict = \
                    {'idle': self.load_images(
                        self.animation_path_lib[name]['idle'],
                        stretch=self.stretch_face),
                     'transition': self.load_images(
                        self.animation_path_lib[name]['transition'],
                        stretch=self.stretch_face)}

                self.animation_lib[name] = animation_dict
                self.optimise_animation(name)
            except Exception as e:
                print("set_blink_animation():", e)

        self.blink_animation = self._animation_generator(
            idle=self.animation_lib[name]['idle'],
            skip_transition=True,
            animation_info_dict=self.eyes_animation_info_dict,
            animation_name=name)
        self.blink_animation_name = name

    def set_eyes_neutral_animation_name(self, name):
        """Set default eye animation."""
        self.eyes_neutral_animation_name = name

    def set_mouth_neutral_animation_name(self, name):
        """Set default mouth animation."""
        self.mouth_neutral_animation_name = name

    def calculate_blit_for_center(self, surface, display_width=None, display_height=None, offset=(0,0)):
        """
        Get blit coordinates for centralising a pygame surface on a display.

        Returns the coordinate corresponding to the top left corner of the
        input surface when the surface is in the center of the display,
        with an optional offset.
        """
        if display_width is None:
            display_width = self.resolution[0]
        if display_height is None:
            display_height = self.resolution[1]

        return (display_width // 2 - surface.get_width() // 2 + offset[0],
                display_height // 2 - surface.get_height() // 2 + offset[1])

################################################################################
# Display Threads
################################################################################

    def set_resolution(self, resolution, mode=None):
        """Set display resolution via (width, height)."""
        self.resolution = resolution

        if mode:
            self.set_display(mode=mode)
        else:
            self.set_display(mode=self.display_mode)

    def set_display(self, mode=None):
        """
        Set display mode.

        Modes:
        0: NOFRAME (borderless windowed)
        1: RESIZABLE (resizable windowed)
        2: FULLSCREEN (fullscreen, but not stretched)
        """
        if self.surface_mode:
            self.display = pygame.Surface(self.resolution)
            self.init_animations()
            return

        if mode is not None:
            self.display_mode = mode
        else:
            self.display_mode += 1

            if self.display_mode > 2:
                self.display_mode = 0

        if self.display_mode == 0:
            self.display = pygame.display.set_mode(self.resolution, pygame.NOFRAME)
        elif self.display_mode == 1:
            self.display = pygame.display.set_mode(self.resolution, pygame.RESIZABLE)
        elif self.display_mode == 2:
            self.display = pygame.display.set_mode(self.resolution, pygame.FULLSCREEN)

        # Re-init display dimensions
        self.display_width, self.display_height = self.resolution
        self.init_animations()

    def init_animations(self):
        with self.lock:
            # Init animations
            self.animation_lib = {}

            if self.enable_blink:
                self.set_blink_animation(self.blink_animation_name)

            self.set_eyes_animation(self.eyes_neutral_animation_name, force_reset_animation=True, no_blink=True)
            self.set_mouth_animation(self.mouth_neutral_animation_name, force_reset_animation=True, no_blink=True)

    def play_blink(self, blink_delay=None):
        """Blink!"""
        try:
            for i in range(len(self.animation_lib[self.blink_animation_name]['idle'])):
                if not self.enable_blink:
                    break

                self._advance_eyes_animation(blink=True)

                if blink_delay:
                    print(blink_delay)
                    pygame.time.delay(blink_delay // self.blink_fps)
                else:
                    pygame.time.delay(1000 // self.blink_fps)
        except Exception as e:
            print("play_blink():", e)

    def start_display_threads(self):
        assert len(self.animation_path_lib) > 0, "You need animations to start the displays!"

        # Open Display, set it to borderless windowed mode
        if self.surface_mode:
            self.set_display(self.display_mode)
            print("FaceModule: SURFACE CREATED")
        else:
            self.set_display(self.display_mode)
            print("FaceModule: DISPLAY CREATED")

        pygame.display.set_icon(pygame.image.load(
            pkg_resources.resource_filename(__name__,
                                            'media/tomoface_logo.png')))
        pygame.display.set_caption('TOMO Face Engine')

        assert len(self.animation_lib) > 0, "You need valid animations to start the displays!"

        Thread(target=self._animation_advance_thread, args=()).start()
        Thread(target=self._display_update_thread, args=()).start()

    def _advance_eyes_animation(self, blink=False):
        """Step eye animation forward one frame."""
        try:
            if blink:
                self.eyes_display_img_prior = next(self.blink_animation)
            else:
                self.eyes_display_img_prior = next(self.eyes_animation)

            self.eyes_width = self.eyes_display_img_prior.get_width()
            self.eyes_height = self.eyes_display_img_prior.get_height()
        except Exception as e:
            print("_advance_eyes_animation():", e)

    def _advance_mouth_animation(self):
        """Step mouth animation forward one frame."""
        if self.no_mouth:
            self.mouth_display_img_prior = self.eyes_display_img_prior

            self.mouth_width = self.eyes_display_img_prior.get_width()
            self.mouth_height = self.eyes_display_img_prior.get_height()
        else:
            try:
                self.mouth_display_img_prior = next(self.mouth_animation)

                self.mouth_width = self.mouth_display_img_prior.get_width()
                self.mouth_height = self.mouth_display_img_prior.get_height()
            except Exception as e:
                print("_advance_mouth_animation():", e)

    def _animation_advance_thread(self):
        """Update which images are used for eyes and mouth."""
        if self.enable_blink:
            self.set_blink_animation(self.blink_animation_name)

        # tomo blink animation
        while self.pygame_running:
            if self.stop_pygame == True:
                print("BLINK CYCLER TERMINATED")
                break

            # tomo_blink enables blinking animations
            if self.enable_blink:
                blink_time_to_wait = random.uniform(3, 7)
                self.last_blink_time = pygame.time.get_ticks()

                # Play transition-idle animation for some time
                while pygame.time.get_ticks() - self.last_blink_time < blink_time_to_wait * 1000:
                    self._advance_eyes_animation()
                    self._advance_mouth_animation()
                    pygame.time.delay(1000 // self.animation_fps)

                self.play_blink() # Blocking!

                # Random chance to blink again
                if random.randint(0, 1) == 1:
                    blink_time_to_wait = random.uniform(0.5, 3)
                    self.last_blink_time = pygame.time.get_ticks()

                    # Play transition-idle animation for some time
                    while pygame.time.get_ticks() - self.last_blink_time < blink_time_to_wait * 1000:
                        self._advance_eyes_animation()
                        self._advance_mouth_animation()
                        pygame.time.delay(1000 // self.animation_fps)

                    self.play_blink() # Blocking!
            else:
                self._advance_eyes_animation()
                self._advance_mouth_animation()
                pygame.time.delay(1000 // self.animation_fps)

    def _display_update_thread(self):
        """Handle face movement controls, squishing, and display updates."""
        while self.eyes_display_img_prior is None:
            pass

        # Init controller variables
        (x, y) = self.calculate_blit_for_center(self.eyes_display_img_prior)
        self.x_goal = x # Init set point
        self.x_pid_output = x # Init PID output
        self.x = x # Init blit input

        self.y_goal = y # Init set point
        self.y_pid_output = y # Init PID output
        self.y = y # Init blit input

        last_blit_rects = []

        while self.pygame_running and not self.stop_pygame:
            # Handle events
            for event in pygame.event.get():
                # If pygame crashes or the user closed the window, quit
                if event.type == pygame.QUIT:
                    if not self.surface_mode:
                        self.stop_pygame = True
                        break

                # Handle one-time keypress events
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self.stop_pygame = True
                        break

                    if event.key == pygame.K_m:
                        if self.no_mouth:
                            self.no_mouth = False
                        else:
                            self.no_mouth = True

                    elif event.key == pygame.K_ESCAPE:
                        self.set_display()

                # Handle mouse events
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.last_blink_time = 0

                # Handle resize events
                elif event.type == pygame.VIDEORESIZE:
                    try:
                        with self.lock:
                            self.resize_buffer = (event.w, event.h)
                    except Exception as e:
                        print(e)

            if self.resize_buffer and pygame.time.get_ticks() - self.last_resize_time > 3000:
                # Filter out minor resizes
                if max(abs(self.resize_buffer[0] - self.resolution[0]),
                       abs(self.resize_buffer[1] - self.resolution[1])) > 10:
                    print("Resize detected! Resizing...")

                    self.set_resolution(self.resize_buffer)
                    self.resize_buffer = None

                self.last_resize_time = pygame.time.get_ticks()

            # Grab held keys
            keys = pygame.key.get_pressed()
            key_pressed = False

            if keys[pygame.K_LEFT]:
                key_pressed = True
                self.x_goal -= 50

            if keys[pygame.K_RIGHT]:
                key_pressed = True
                self.x_goal += 50

            if keys[pygame.K_DOWN]:
                key_pressed = True
                self.y_goal += 50

            if keys[pygame.K_UP]:
                key_pressed = True
                self.y_goal -= 50

            if not key_pressed:
                # If there have been no recent position commands, center face
                if pygame.time.get_ticks() - self.last_position_time > self.position_timeout:
                    (self.x_goal, self.y_goal) = self.calculate_blit_for_center(self.eyes_display_img_prior)

            # If timeout for either eyes or mouth animation has been reached,
            # reset them to the current neutral state (unless they are already there)
            if pygame.time.get_ticks() - self.last_eyes_animation_time > self.eyes_animation_timeout:
                if self.eyes_animation_name != self.eyes_neutral_animation_name:
                    self.set_eyes_animation(self.eyes_neutral_animation_name, skip_transition=self.skip_neutral_transition)

            if pygame.time.get_ticks() - self.last_mouth_animation_time > self.mouth_animation_timeout:
                if self.mouth_animation_name != self.mouth_neutral_animation_name:
                    self.set_mouth_animation(self.mouth_neutral_animation_name, skip_transition=self.skip_neutral_transition)

            # Limit the goal requests
            if self.x_goal < 0:
                self.x_goal = 0
            if self.x_goal > self.display_width - self.eyes_width:
                self.x_goal = self.display_width - self.eyes_width

            if self.no_mouth:
                y_upper_limit = self.display_height - self.eyes_height * (1 + self.y_padding)
                y_lower_limit = self.y_padding * self.eyes_height
            elif self.mouth_offset[1] >= 0: # Mouth below eyes
                y_upper_limit = self.display_height - self.eyes_height * (1 + self.y_padding) - self.mouth_offset[1]
                y_lower_limit = self.y_padding * self.eyes_height
            else: # Mouth above eyes
                y_upper_limit = self.display_height - self.eyes_height * (1 + self.y_padding)
                y_lower_limit = self.y_padding * self.eyes_height - self.mouth_offset[1]

            if self.y_goal > y_upper_limit:
                self.y_goal = y_upper_limit
            if self.y_goal < y_lower_limit:
                self.y_goal = y_lower_limit

            # Compute PID control for eyes
            try:
                self.x_pid_output += self.x_pid.compute(self.x_goal, self.x)
                self.y_pid_output += self.y_pid.compute(self.y_goal, self.y)

                if self.x_pid_output != None:
                    self.x = self.x_pid_output

                if self.y_pid_output != None:
                    self.y = self.y_pid_output
            except:
                pass

            if self.no_mouth:
                y_upper_squash_limit = self.display_height - self.eyes_height * (1 + self.squash_window + self.y_padding)
                y_lower_squash_limit = (self.squash_window + self.y_padding) * self.eyes_height
                y_face_top, y_face_bottom = self.y, self.y
            elif self.mouth_offset[1] >= 0: # Mouth below eyes
                y_upper_squash_limit = self.display_height - self.eyes_height * (1 + self.squash_window + self.y_padding) - self.mouth_offset[1]
                y_lower_squash_limit = (self.squash_window + self.y_padding) * self.eyes_height
                y_face_top, y_face_bottom = self.y, self.y + self.mouth_offset[1]
            else: # Mouth above eyes
                y_upper_squash_limit = self.display_height - self.eyes_height * (1 + self.squash_window + self.y_padding)
                y_lower_squash_limit = (self.squash_window + self.y_padding) * self.eyes_height - self.mouth_offset[1]
                y_face_top, y_face_bottom = self.y + self.mouth_offset[1], self.y

            # Squash eyes if face is near the bottom of the screen
            # Note: Upper limit here refers to the magnitude of the y value
            # Higher y values refers to lower screen positions
            if y_face_bottom > y_upper_squash_limit:
                squash_percentage = (y_face_bottom - y_upper_squash_limit) / (y_upper_limit - y_upper_squash_limit)
                squashed_eyes_x = self.eyes_width * (1 + self.squash_amount_x * squash_percentage)
                squashed_eyes_y = self.eyes_height * (1 - self.squash_amount_y * squash_percentage)

                x_eyes_shf = self.x - (squashed_eyes_x - self.eyes_width) / 2
                y_eyes_shf = self.y + (self.eyes_height - squashed_eyes_y) # Compensate for translation due to scale

                try:
                    if self.performance_mode:
                        self.eyes_display_img = pygame.transform.scale(self.eyes_display_img_prior, (int(squashed_eyes_x), int(squashed_eyes_y))) #display_height // 2))
                    else:
                        self.eyes_display_img = pygame.transform.smoothscale(self.eyes_display_img_prior, (int(squashed_eyes_x), int(squashed_eyes_y))) #display_height // 2))
                except Exception as e:
                    print(e)

            # Squash eyes if face is near the top of the screen
            elif y_face_top < y_lower_squash_limit:
                squash_percentage = (y_face_top - y_lower_squash_limit) / (y_lower_limit - y_lower_squash_limit)
                squashed_eyes_x = self.eyes_width * (1 + self.squash_amount_x * squash_percentage)
                squashed_eyes_y = self.eyes_height * (1 - self.squash_amount_y * squash_percentage)

                x_eyes_shf = self.x - (squashed_eyes_x - self.eyes_width) / 2
                y_eyes_shf = self.y

                try:
                    if self.performance_mode:
                        self.eyes_display_img = pygame.transform.scale(self.eyes_display_img_prior, (int(squashed_eyes_x), int(squashed_eyes_y))) #display_height // 2))
                    else:
                        self.eyes_display_img = pygame.transform.smoothscale(self.eyes_display_img_prior, (int(squashed_eyes_x), int(squashed_eyes_y))) #display_height // 2))
                except Exception as e:
                    print(e)

            else:
                self.eyes_display_img = self.eyes_display_img_prior
                x_eyes_shf = self.x
                y_eyes_shf = self.y

            if not self.no_mouth:
                x_mouth, y_mouth = self.x + self.mouth_offset[0], self.y + self.mouth_offset[1]

                # Squash mouth if face is near the bottom of the screen
                if y_face_bottom > y_upper_squash_limit:
                    squash_percentage = (y_face_bottom - y_upper_squash_limit) / (y_upper_limit - y_upper_squash_limit)
                    squashed_mouth_x = self.mouth_width * (1 + self.squash_amount_x * squash_percentage)
                    squashed_mouth_y = self.mouth_height * (1 - self.squash_amount_y * squash_percentage)

                    x_mouth_shf = x_mouth - (squashed_mouth_x - self.mouth_width) / 2
                    y_mouth_shf = y_mouth + (self.mouth_height - squashed_mouth_y) # Compensate for translation due to scale

                    try:
                        if self.performance_mode:
                            self.mouth_display_img = pygame.transform.scale(self.mouth_display_img_prior, (int(squashed_mouth_x), int(squashed_mouth_y)))
                        else:
                            self.mouth_display_img = pygame.transform.smoothscale(self.mouth_display_img_prior, (int(squashed_mouth_x), int(squashed_mouth_y)))
                    except Exception as e:
                        print(e)

                # Squash mouth if they're near the top of the screen
                elif y_face_top < y_lower_squash_limit:
                    squash_percentage = (y_face_top - y_lower_squash_limit) / (y_lower_limit - y_lower_squash_limit)
                    squashed_mouth_x = self.mouth_width * (1 + self.squash_amount_x * squash_percentage)
                    squashed_mouth_y = self.mouth_height * (1 - self.squash_amount_y * squash_percentage)

                    x_mouth_shf = x_mouth - (squashed_mouth_x - self.mouth_width) / 2
                    y_mouth_shf = y_mouth

                    try:
                        if self.performance_mode:
                            self.mouth_display_img = pygame.transform.scale(self.mouth_display_img_prior, (int(squashed_mouth_x), int(squashed_mouth_y)))
                        else:
                            self.mouth_display_img = pygame.transform.smoothscale(self.mouth_display_img_prior, (int(squashed_mouth_x), int(squashed_mouth_y)))
                    except Exception as e:
                        print(e)

                else:
                    self.mouth_display_img = self.mouth_display_img_prior
                    x_mouth_shf = x_mouth
                    y_mouth_shf = y_mouth

            # Fill the screen with white
            self.display.fill(self.background_colour)

            # Compute bob
            bob = self.bob_amount * (math.sin(pygame.time.get_ticks() / 1000
                                     * 2 * math.pi
                                     * self.bob_frequency))

            # Track modified areas
            padding_x = self.display.get_width() // 50
            padding_y = self.display.get_height() // 50

            blit_rects = last_blit_rects
            new_blit_rects = []

            # Execute the eye translation
            self.display.blit(self.eyes_display_img, (x_eyes_shf, y_eyes_shf + bob))
            new_blit_rects.append(pygame.Rect((x_eyes_shf - padding_x, y_eyes_shf + bob - padding_y),
                                  (self.eyes_display_img.get_width() + padding_x * 2,
                                   self.eyes_display_img.get_height() + padding_y * 2)))

            if not self.no_mouth:
                self.display.blit(self.mouth_display_img, (x_mouth_shf, y_mouth_shf + bob))
                new_blit_rects.append(pygame.Rect((x_mouth_shf - padding_x, y_mouth_shf + bob - padding_y),
                                      (self.mouth_display_img.get_width() + padding_x * 2,
                                       self.mouth_display_img.get_height() + padding_y * 2)))

            if self.overlay_image_flag:
                self.display.blit(self.overlay_image, self.overlay_image_offset)
                new_blit_rects.append(pygame.Rect(self.overlay_image_offset, self.overlay_image.get_size()))

            last_blit_rects = new_blit_rects
            blit_rects.extend(new_blit_rects)

            # Update the frame and tick the clock (Best effort for 60FPS)
            if self.surface_mode:
                self.output_surface.blit(self.display, (0,0))
            else:
                # TODO: OPTION TO ROTATE
                pygame.display.update(blit_rects)

            self.clock.tick(self.motion_fps)

        self.pygame_running = False
        pygame.display.quit()

if __name__ == "__main__":
    from pid import PIDController
    from utils import add_animations, add_single_animation, \
                      parse_animation_path, load_images

    face_module = TomoFaceModule(eyes_neutral_animation_name="happy_eyes",
                                 mouth_neutral_animation_name="happy_mouth", blink_animation_name="blink",
                                 start_display=True,
                                 # resolution=(1920, 1080),
                                 resolution=(480, 270),
                                 no_mouth=False, enable_blink=True, mouth_offset=(0, 10), background_colour=(0, 0, 0),
                                 y_padding=0.05,
                                 squash_window=0.25,
                                 squash_amount_x=0.2, squash_amount_y=0.15,
                                 bob_amount=0, bob_frequency=0.4,
                                 skip_neutral_transition=True)

    face_module.animation_lib
    eyes_animations = [x for x in face_module.animation_lib.keys() if "eyes" in x and not "test" in x]
    mouth_animations = [x for x in face_module.animation_lib.keys() if "mouth" in x and not "test" in x]


    time.sleep(5)
    face_module.set_eyes_animation("inlove_eyess", skip_transition=True)
