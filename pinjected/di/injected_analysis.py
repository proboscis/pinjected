import inspect
import sys

def get_instance_origin(package_name):
    from loguru import logger
    # Get the current frame
    #logger.debug(f"trying to get the instance origin")


    current_frame = sys._getframe()

    # Go up the call stack to find the frame outside the given package
    while current_frame:
        # Get the frame information

        # Check if the frame's module is not in the specified package
        # This 'getmodule' is taking way too much time (80%)
        # Actually for configurations we don't need this... canwe configure this?
        # or maybe we should memoize,, but the key is current frame :(
        if '__module__' not in current_frame.f_globals:
            module = inspect.getmodule(current_frame)
        else:
            module = current_frame.f_globals['__module__']
        #module = inspect.getmodule(current_frame)
        if module is not None and not module.__name__.startswith(package_name):
            frame_info = inspect.getframeinfo(current_frame)
            # maybe this is taking so much time?
            #logger.debug(f"found instance origin:{frame_info.filename}")
            return frame_info

        # Move to the next frame in the call stack
        current_frame = current_frame.f_back

def get_instance_origin2(package_name):
    # Get the current frame

    current_frame = inspect.currentframe()

    # Go up the call stack to find the frame outside the given package
    while current_frame:
        # Get the frame information
        frame_info = inspect.getframeinfo(current_frame)

        # Check if the frame's module is not in the specified package
        module = inspect.getmodule(current_frame)
        if module is not None and not module.__name__.startswith(package_name):
            return frame_info

        # Move to the next frame in the call stack
        current_frame = current_frame.f_back
