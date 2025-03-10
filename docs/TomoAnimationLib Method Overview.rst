Processing Methods:
  - :meth:`~TomoAnimationLib.aspect_scale()`: Get scaled image dimensions \
    while retaining aspect ratio.
  - :meth:`~TomoAnimationLib.load_images()`: Compute and load rescaled \
    images as pygame surfaces.
  - :meth:`~TomoAnimationLib.set_display()`: Set pygame display object to\
    optimise images towards.

Sanity Check Methods:
  - :meth:`~TomoAnimationLib.is_image_file()`: Check if a given file is a \
    valid image file.
  - :meth:`~TomoAnimationLib.is_valid_animation()`: Check if a given path \
    is a valid animation directory.

IO Methods:
  - :meth:`~TomoAnimationLib.add_animations()`: Get scaled image \
    dimensions while retaining aspect ratio.
  - :meth:`~TomoAnimationLib.add_and_load_animations()`: Load and add \
    animations from a path.
  - :meth:`~TomoAnimationLib.add_single_subanimation()`: Add a single \
    sub-animation into path lib without loading it.
  - :meth:`~TomoAnimationLib.add_and_load_single_subanimation()`: Add and \
    load a single sub-animation.

Animation Management Methods:
  - :meth:`~TomoAnimationLib.load_animations()`: Load all animations in the \
    path lib into the frame lib.
  - :meth:`~TomoAnimationLib.load_animation()`: Load an animation in the \
    path lib into the frame lib.
  - :meth:`~TomoAnimationLib.unload_animation()`: Unload a single \
    animation’s frame images to clear memory.
  - :meth:`~TomoAnimationLib.unload_animations()`: Unload animation frame \
    images to clear memory.
  - :meth:`~TomoAnimationLib.remove_animation()`: Remove a single animation \
    from the frame and path libraries.
  - :meth:`~TomoAnimationLib.remove_animations()`: Remove animations from \
    the frame and path libraries.
  - :meth:`~TomoAnimationLib.create_animation()`: Create and configure a \
    playable :class:`~TomoAnimation.TomoAnimation()`.
  - :meth:`~TomoAnimationLib.update_animation()`: Update an animation while \
    preserving its sequence and state.

Private Methods:
  - :meth:`~TomoAnimationLib._optimise_animation()`: Optimise image format \
    for an animation's images.
  - :meth:`~TomoAnimationLib._load_animation()`: Load an animation in the \
    path lib into the frame lib.
  - :meth:`~TomoAnimationLib._parse_animation_path()`: Parse all valid \
    animation paths in a directory as a dict.
  - :meth:`~TomoAnimationLib._generate_playback_list()`: Parse playback \
    file and generate playback list.
