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
- animation_advance_thread thread
- display_update_thread thread
"""

try:
    from .lib import PIDController
except:
    from lib import PIDController
from threading import Thread

import time
import math
import pygame
import random
import sys
import os

################################################################################
# Helper Functions
################################################################################

def is_image_file(filename):
    """Check if a given file is an image file."""
    return any([filename.endswith(img_type) for img_type in [".jpg", ".png", ".gif"]])

def is_valid_animation(path, verbose=True):
    """Check if a given path is a valid animation folder."""
    try:
        if "idle" in os.listdir(path) or "transition" in os.listdir(path):
            return True
        else:
            if verbose:
                print(path, "is not a valid animation folder! It needs an /idle or /transition folder!")
            return False
    except:
        return False

def generate_playback_list(data, delimiter=" ", default_delay=1):
    """Parse playback string and generate list of tuples of (frame_index, default_delay)"""
    if len(data) == 0:
        return []

    playback_list = data.strip().split("\n")
    output = []

    for row_no, frame in enumerate(playback_list, 1):
        split_frame = tuple([int(x) for x in frame.strip().split(delimiter)])

        assert len(split_frame) <= 2, "Frame %d is of invalid form!" % (row_no)

        if len(split_frame) == 1:
            output.append((split_frame[0], default_delay))
        if len(split_frame) == 2:
            output.append(split_frame)

    return output

def parse_animation_path(path, verbose=True):
    """Find all valid animations in a directory and load them."""
    output = {}

    # Iterate through all possible paths
    for folder_path in os.listdir(path):
        animation_dict = {'transition': [], 'idle': [], 'transition_playback': [], 'idle_playback': [], 'animation_name': ""}
        animation_path = path + "/" + folder_path

        # And only proceed if the animation path is valid
        if is_valid_animation(animation_path, verbose):
            for sub_animation in ["transition", "idle"]:
                try:
                    sub_animation_path = animation_path + "/" + sub_animation + "/"
                    animation_dict['animation_name'] = animation_path

                    filenames = os.listdir(sub_animation_path)
                    frames = [sub_animation_path + frame for frame in filenames if is_image_file(frame)]
                    frames.sort()
                    animation_dict[sub_animation] = frames

                    if "frames" in filenames:
                        with open(sub_animation_path + "/frames", "r") as f:
                            animation_dict[sub_animation + "_playback"] = generate_playback_list(f.read())
                except Exception as e:
                    print("is_valid_animation():", e)

            output[folder_path] = animation_dict

    return output

# Source http://www.pygame.org/pcr/transform_scale/
def aspect_scale(img, rescale_tuple):
    """Get scaled image dimensions while retaining aspect ratio."""
    bx, by = rescale_tuple
    ix,iy = img.get_size()

    if ix > iy:
        scale_factor = bx/float(ix)
        sy = scale_factor * iy
        if sy > by:
            scale_factor = by/float(iy)
            sx = scale_factor * ix
            sy = by
        else:
            sx = bx
    else:
        scale_factor = by/float(iy)
        sx = scale_factor * ix
        if sx > bx:
            scale_factor = bx/float(ix)
            sx = bx
            sy = scale_factor * iy
        else:
            sy = by

    return int(sx), int(sy)

################################################################################
# Class
################################################################################

class TomoFaceModule():
    def __init__(self, init_pygame=True, animation_path="",
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
                 no_mouth=False,
                 overlay_image=False, overlay_image_offset=(0,0),
                 resolution=None,
                 surface_mode=False,
                 y_padding=0.05,
                 squash_window=0.15, squash_amount_x=0.5, squash_amount_y=0.5,
                 bob_amount=0, bob_frequency=0.2,
                 skip_neutral_transition=False):

        self.pygame_running = False
        self.stop_pygame = False
        self.resolution = resolution
        # TODO: Organise these
        self.y_padding = y_padding
        self.squash_window = squash_window
        self.squash_amount_x = squash_amount_x
        self.squash_amount_y = squash_amount_y
        self.bob_amount = bob_amount
        self.bob_frequency = bob_frequency
        self.skip_neutral_transition = skip_neutral_transition

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
        self.eyes_last_animation_name = None

        self.mouth_display_img = None
        self.mouth_display_img_prior = None
        self.mouth_animation = None
        self.mouth_animation_name = None
        self.mouth_last_animation_name = None

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
        pygame.init()

        # Init Display Parameters
        self.infoObject = pygame.display.Info()

        if self.resolution:
            self.display_width, self.display_height = self.resolution
        else:
            (self.display_width, self.display_height) = self.display_size = (self.infoObject.current_w, self.infoObject.current_h)

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
                rescale_tuple = (self.display_width // 2, self.display_height // 2)

            if stretch: # Stretch images to fit display
                return [pygame.transform.smoothscale(pygame.image.load(image), rescale_tuple) for image in img_path_list]
            else: # Otherwise, preserve aspect ratio
                return [pygame.transform.smoothscale(pygame.image.load(image), \
                        aspect_scale(pygame.image.load(image), rescale_tuple)) \
                        for image in img_path_list]
        else:
            print("Pygame not started! Call .init_pygame() to start!")
            return []

    def add_single_animation(self, name, sub_name,
                             img_path_list, playback_list=[],
                             rescale_tuple=None):
        """Load single sub-animation."""
        self.animation_lib[name][sub_name] = self.load_images(img_path_list, rescale_tuple)
        self.animation_lib[name][sub_name + "_playback"] = playback_list

    def add_animations(self, animation_path, verbose=True, rescale_tuple=None):
        """Load and add animations from a given path."""
        for animation_name, animation_path_dict in parse_animation_path(animation_path, verbose=True).items():
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
                animation_path_dict[property] = self.load_images(contents, rescale_tuple)

            # And update the visual library
            self.animation_lib[animation_name] = animation_path_dict

    def animation_generator(self, animation_dict=None, default_delay=1, transition=[], idle=[],
                            transition_playback_list=[], idle_playback_list=[], skip_transition=False):
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
                    for i in range(frame_delay):
                        yield transition[frame_index]
                except Exception as e:
                    print("animation_generator():",e)
                    print(animation_dict)
                    print("Transition frame", frame_index, "does not exist!")
                    yield None

        # Play idle on loop
        while True:
            for frame_index, frame_delay in idle_playback_list:
                try:
                    for i in range(frame_delay):
                        yield idle[frame_index]
                except Exception as e:
                    print(e)
                    print("Idle frame", frame_index, "does not exist!")
                    yield None

    def set_position_goal(self, x, y):
        """Set target position of face."""
        self.x_goal = x
        self.y_goal = y

        self.last_position_time = pygame.time.get_ticks()

    # TODO
    def set_offset_goal(self, x, y):
        """Set target position of face."""
        self.x_goal = x
        self.y_goal = y

        self.last_position_time = pygame.time.get_ticks()

    def increment_position_goal(self, x, y):
        """Increment target position of face."""
        self.x_goal += x
        self.y_goal += y

        self.last_position_time = pygame.time.get_ticks()

    def set_eyes_animation(self, animation_name, default_delay=1, timeout=None, skip_transition=False):
        """Set current eye animation."""
        self.eyes_animation = self.animation_generator(self.animation_lib[animation_name], default_delay=default_delay, skip_transition=skip_transition)

        self.eyes_last_animation_name = self.eyes_animation_name
        self.eyes_animation_name = animation_name

        if timeout is None:
            self.eyes_animation_timeout = self.default_eyes_animation_timeout
        else:
            self.eyes_animation_timeout = timeout

        self.last_eyes_animation_time = pygame.time.get_ticks()

    def set_mouth_animation(self, animation_name, default_delay=1, timeout=None, skip_transition=False):
        """Set current mouth animation."""
        if self.no_mouth:
            self.mouth_animation_timeout = self.eyes_animation_timeout
            return

        self.mouth_animation = self.animation_generator(self.animation_lib[animation_name], default_delay=default_delay, skip_transition=skip_transition)

        self.mouth_last_animation_name = self.mouth_animation_name
        self.mouth_animation_name = animation_name

        if timeout is None:
            self.mouth_animation_timeout = self.default_mouth_animation_timeout
        else:
            self.mouth_animation_timeout = timeout

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

    def set_blink_animation(self, name, default_delay=1):
        """Set blink animation."""
        self.blink_animation = self.animation_generator(idle=self.animation_lib[name]['idle'], skip_transition=True)
        self.blink_animation_name = name

    def set_eyes_neutral_animation_name(self, name):
        """Set default eye animation."""
        self.eyes_neutral_animation_name = name

    def set_mouth_neutral_animation_name(self, name):
        """Set default mouth animation."""
        self.mouth_neutral_animation_name = name

    def advance_eyes_animation(self, blink=False):
        """Step eye animation forward one frame."""
        if blink:
            self.eyes_display_img_prior = next(self.blink_animation)
        else:
            self.eyes_display_img_prior = next(self.eyes_animation)

        self.eyes_width = self.eyes_display_img_prior.get_width()
        self.eyes_height = self.eyes_display_img_prior.get_height()

    def advance_mouth_animation(self):
        """Step mouth animation forward one frame."""
        if self.no_mouth:
            self.mouth_display_img_prior = self.eyes_display_img_prior

            self.mouth_width = self.eyes_display_img_prior.get_width()
            self.mouth_height = self.eyes_display_img_prior.get_height()
        else:
            self.mouth_display_img_prior = next(self.mouth_animation)

            self.mouth_width = self.mouth_display_img_prior.get_width()
            self.mouth_height = self.mouth_display_img_prior.get_height()

    def calculate_blit_for_center(self, surface, display_width=None, display_height=None, offset=(0,0)):
        """
        Get blit coordinates for centralising a pygame surface on a display.

        Returns the coordinate corresponding to the top left corner of the
        input surface when the surface is in the center of the display,
        with an optional offset.
        """
        if display_width is None:
            display_width = self.display_width
        if display_height is None:
            display_height = self.display_height

        return (display_width // 2 - surface.get_width() // 2 + offset[0],
                display_height // 2 - surface.get_height() // 2 + offset[1])

################################################################################
# Display Threads
################################################################################

    def play_blink(self):
        """Blink!"""
        for i in range(len(self.animation_lib[self.blink_animation_name]['idle'])):
            if not self.enable_blink:
                break

            self.advance_eyes_animation(blink=True)
            pygame.time.delay(1000 // self.blink_fps)

    def start_display_threads(self):
        assert len(self.animation_lib) > 0, "You need animations to start the displays!"

        # Open Display, set it to borderless windowed mode
        if self.surface_mode:
            print("FaceModule: SURFACE CREATED")
            if self.resolution:
                self.display = pygame.Surface(self.resolution)
            else:
                self.display = pygame.Surface(self.display_size)
        else:
            print("FaceModule: DISPLAY CREATED")
            if self.resolution:
                self.display = pygame.display.set_mode(self.resolution, pygame.NOFRAME)
            else:
                self.display = pygame.display.set_mode(self.display_size, pygame.NOFRAME)

        pygame.display.set_caption('TOMO!')

        self.set_eyes_animation(self.eyes_neutral_animation_name)
        self.set_mouth_animation(self.mouth_neutral_animation_name)

        Thread(target=self.animation_advance_thread, args=()).start()
        Thread(target=self.display_update_thread, args=()).start()

    def animation_advance_thread(self):
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
                    self.advance_eyes_animation()
                    self.advance_mouth_animation()
                    pygame.time.delay(1000 // self.animation_fps)

                self.play_blink() # Blocking!

                # Random chance to blink again
                if random.randint(0, 1) == 1:
                    blink_time_to_wait = random.uniform(0.5, 3)
                    self.last_blink_time = pygame.time.get_ticks()

                    # Play transition-idle animation for some time
                    while pygame.time.get_ticks() - self.last_blink_time < blink_time_to_wait * 1000:
                        self.advance_eyes_animation()
                        self.advance_mouth_animation()
                        pygame.time.delay(1000 // self.animation_fps)

                    self.play_blink() # Blocking!
            else:
                self.advance_eyes_animation()
                self.advance_mouth_animation()
                pygame.time.delay(1000 // self.animation_fps)

    def display_update_thread(self):
        """Handle face movement controls, squishing, and display updates."""
        self.set_eyes_animation(self.eyes_neutral_animation_name)
        self.set_mouth_animation(self.mouth_neutral_animation_name)

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

        while self.pygame_running and not self.stop_pygame:
            # If pygame crashes, quit
            if not self.surface_mode:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.stop_pygame = True
                        break

            # Grab key events
            keys = pygame.key.get_pressed()

            if keys[pygame.K_q]:
                self.stop_pygame = True
                break

            if keys[pygame.K_LEFT]:
                self.x_goal -= 50

            elif keys[pygame.K_RIGHT]:
                self.x_goal += 50

            elif keys[pygame.K_DOWN]:
                self.y_goal += 50

            elif keys[pygame.K_UP]:
                self.y_goal -= 50

            elif keys[pygame.K_ESCAPE]:
                if self.display.get_flags() & pygame.NOFRAME:
                    pygame.display.set_mode(self.display_size)
                else:
                    pygame.display.set_mode(self.display_size, pygame.NOFRAME)

            else:
                # If there have been no recent position commands, center face
                if pygame.time.get_ticks() - self.last_position_time > self.position_timeout:
                    (self.x_goal, self.y_goal) = self.calculate_blit_for_center(self.eyes_display_img_prior)

            # If timeout for either eyes or mouth animation has been reached,
            # reset them to the current neutral state (unless they are already there)
            if pygame.time.get_ticks() - self.last_eyes_animation_time > self.eyes_animation_timeout:
                if self.eyes_animation_name != self.eyes_neutral_animation_name:
                    self.set_eyes_animation(self.eyes_neutral_animation_name)

            if pygame.time.get_ticks() - self.last_mouth_animation_time > self.mouth_animation_timeout:
                if self.mouth_animation_name != self.mouth_neutral_animation_name:
                    self.set_mouth_animation(self.mouth_neutral_animation_name)

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
                squash_percentage = (y_face_bottom - y_upper_squash_limit) / (y_upper_limit - y_upper_squash_limit) * 100
                squashed_eyes_x = self.eyes_width + self.squash_amount_x * squash_percentage
                squashed_eyes_y = self.eyes_height - self.squash_amount_y * squash_percentage

                self.eyes_display_img = pygame.transform.smoothscale(self.eyes_display_img_prior, (int(squashed_eyes_x), int(squashed_eyes_y))) #display_height // 2))

                x_eyes_shf = self.x - (squashed_eyes_x - self.eyes_width) / 2
                y_eyes_shf = self.y + (self.eyes_height - squashed_eyes_y) # Compensate for translation due to scale

            # Squash eyes if face is near the top of the screen
            elif y_face_top < y_lower_squash_limit:
                squash_percentage = (y_face_top - y_lower_squash_limit) / (y_lower_limit - y_lower_squash_limit) * 100
                squashed_eyes_x = self.eyes_width + self.squash_amount_x * squash_percentage
                squashed_eyes_y = self.eyes_height - self.squash_amount_y * squash_percentage

                x_eyes_shf = self.x - (squashed_eyes_x - self.eyes_width) / 2
                y_eyes_shf = self.y

                self.eyes_display_img = pygame.transform.smoothscale(self.eyes_display_img_prior, (int(squashed_eyes_x), int(squashed_eyes_y))) #display_height // 2))

            else:
                self.eyes_display_img = self.eyes_display_img_prior
                x_eyes_shf = self.x
                y_eyes_shf = self.y

            if not self.no_mouth:
                x_mouth, y_mouth = self.x + self.mouth_offset[0], self.y + self.mouth_offset[1]

                # Squash mouth if face is near the bottom of the screen
                if y_face_bottom > y_upper_squash_limit:
                    squash_percentage = (y_face_bottom - y_upper_squash_limit) / (y_upper_limit - y_upper_squash_limit) * 100
                    squashed_mouth_x = self.mouth_width + self.squash_amount_x * squash_percentage
                    squashed_mouth_y = self.mouth_height - self.squash_amount_y * squash_percentage

                    x_mouth_shf = x_mouth - (squashed_mouth_x - self.mouth_width) / 2
                    y_mouth_shf = y_mouth + (self.mouth_height - squashed_mouth_y) # Compensate for translation due to scale

                    self.mouth_display_img = pygame.transform.smoothscale(self.mouth_display_img_prior, (int(squashed_mouth_x), int(squashed_mouth_y)))

                # Squash mouth if they're near the top of the screen
                elif y_face_top < y_lower_squash_limit:
                    squash_percentage = (y_face_top - y_lower_squash_limit) / (y_lower_limit - y_lower_squash_limit) * 100
                    squashed_mouth_x = self.mouth_width + self.squash_amount_x * squash_percentage
                    squashed_mouth_y = self.mouth_height - self.squash_amount_y * squash_percentage

                    x_mouth_shf = x_mouth - (squashed_mouth_x - self.mouth_width) / 2
                    y_mouth_shf = y_mouth

                    self.mouth_display_img = pygame.transform.smoothscale(self.mouth_display_img_prior, (int(squashed_mouth_x), int(squashed_mouth_y)))

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

            # Execute the eye translation
            self.display.blit(self.eyes_display_img, (x_eyes_shf, y_eyes_shf + bob))

            if not self.no_mouth:
                self.display.blit(self.mouth_display_img, (x_mouth_shf, y_mouth_shf + bob))

            if self.overlay_image_flag:
                self.display.blit(self.overlay_image, self.overlay_image_offset)

            # Update the frame and tick the clock (Best effort for 60FPS)
            if self.surface_mode:
                self.output_surface.blit(self.display, (0,0))
            else:
                pygame.display.update()

            self.clock.tick(self.motion_fps)

        self.pygame_running = False
        pygame.quit()

if __name__ == "__main__":
    pass

    face_module = TomoFaceModule(animation_path="tomo_animations", eyes_neutral_animation_name="happy_eyes",
                                 mouth_neutral_animation_name="happy_mouth", blink_animation_name="blink",
                                 start_display=True, resolution=(1920, 1080),
                                 no_mouth=False, enable_blink=True, mouth_offset=(0, 0), background_colour=(0, 0, 0),
                                 y_padding=0.05,
                                 squash_window=0.25,
                                 squash_amount_x=0.75, squash_amount_y=0.75)

    face_module.animation_lib

    time.sleep(5)
    face_module.set_eyes_animation("inlove_eyess", skip_transition=True)
