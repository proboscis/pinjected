import inspect
import sys

def get_instance_origin(package_name):
    # Get the current frame


    current_frame = sys._getframe()

    # Go up the call stack to find the frame outside the given package
    while current_frame:
        # Get the frame information

        # Check if the frame's module is not in the specified package
        module = inspect.getmodule(current_frame)
        if module is not None and not module.__name__.startswith(package_name):
            frame_info = inspect.getframeinfo(current_frame)
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
