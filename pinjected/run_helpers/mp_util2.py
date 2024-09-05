import multiprocessing
import sys
import io

def redirect_output(queue, func, *args, **kwargs):
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    # Redirect stdout and stderr to in-memory buffers
    sys.stdout = stdout_buffer
    sys.stderr = stderr_buffer

    try:
        func(*args, **kwargs)
    finally:
        # Restore original stdout and stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        # Get the contents of the buffers
        stdout_output = stdout_buffer.getvalue()
        stderr_output = stderr_buffer.getvalue()

        # Send the captured output through the queue
        queue.put((stdout_output, stderr_output))

def capture_output(func, *args, **kwargs):
    # Create a queue for communication
    queue = multiprocessing.Queue()

    # Create and start the process
    process = multiprocessing.Process(
        target=redirect_output,
        args=(queue, func) + args,
        kwargs=kwargs
    )
    process.start()
    process.join()

    # Get the captured output from the queue
    stdout_data, stderr_data = queue.get()

    return stdout_data, stderr_data

# Example usage
def example_function(message):
    print(f"This is stdout: {message}")
    print(f"This is stderr: {message}", file=sys.stderr)
    # Example of using a library that writes directly to stdout
    import os
    os.system('echo "This is from os.system"')

if __name__ == "__main__":
    stdout, stderr = capture_output(example_function, "Hello, World!")

    print("Captured stdout:")
    print(stdout)
    print("\nCaptured stderr:")
    print(stderr)