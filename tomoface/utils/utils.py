import pygame
import os

################################################################################
# Helper Functions
################################################################################

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
# IO Functions
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
                    print("parse_animation_path():", e)

            output[folder_path] = animation_dict

    return output

def load_images(img_path_list, rescale_tuple, stretch=False):
    """Compute and load rescaled images as pygame surfaces."""
    if stretch: # Stretch images to fit display
        return [pygame.transform.smoothscale(pygame.image.load(image),
                                             rescale_tuple) \
                for image in img_path_list]
    else: # Otherwise, preserve aspect ratio
        return [pygame.transform.smoothscale(pygame.image.load(image), \
                aspect_scale(pygame.image.load(image), rescale_tuple)) \
                for image in img_path_list]

def add_single_animation(name, sub_name,
                         img_path_list, playback_list=[],
                         animation_path_lib=None):
    """Add a single sub-animation to an animation path library."""
    if not animation_path_lib:
        animation_path_lib = {name: {}}
    else:
        if not animation_path_lib.get(name):
            animation_path_lib = {name: {}}

    animation_path_lib[name][sub_name] = img_path_list
    animation_path_lib[name][sub_name + "_playback"] = playback_list

    return animation_path_lib

def add_animations(animation_path, verbose=True, animation_path_lib={}):
    """
    Add animation paths from a given overall path to an animation path library.

    Traverses each generated animation dictionary from the given path,
    and updates the visual path library.

    This initialises the animation lib lazily!
    To avoid lazy initialisation, use add_and_load_animations()

    Loading, rescaling, and converting the animation surfaces will happen
    later when animations are generated."""
    for animation_name, animation_path_dict in parse_animation_path(animation_path, verbose=verbose).items():
        animation_path_lib[animation_name] = animation_path_dict

    return animation_path_lib

def add_and_load_single_animation(name, sub_name,
                                  rescale_tuple,
                                  img_path_list, playback_list=[],
                                  stretch=False,
                                  animation_path_lib=None,
                                  animation_lib=None):
    """Add and load a single sub-animation."""
    if not animation_path_lib:
        animation_path_lib = {name: {}}

    if not animation_lib:
        animation_lib = {name: {}}

    animation_path_lib = add_single_animation(name, sub_name, img_path_list,
                                              playback_list, animation_path_lib)

    animation_lib[name][sub_name] = load_images(img_path_list, rescale_tuple, stretch)
    animation_lib[name][sub_name + "_playback"] = playback_list

    return animation_lib, animation_path_lib

def add_and_load_animations(animation_path, rescale_tuple, verbose=True,
                            stretch=False,
                            animation_path_lib={}, animation_lib={}):
    """Load and add animations from a given path."""
    animation_path_lib = add_animations(animation_path,
                                        verbose=verbose,
                                        animation_path_lib=animation_path_lib)

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
            animation_path_dict[property] = load_images(contents, rescale_tuple, stretch)

        # And update the visual library
        animation_lib[animation_name] = animation_path_dict

    return animation_lib, animation_path_lib
