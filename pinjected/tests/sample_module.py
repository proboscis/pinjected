from pinjected import instance

leaf1 = "leaf1 value"
leaf2 = "leaf2 value"


@instance
def middle1(leaf1):
    return f"middle using {leaf1}"


@instance
def middle2(leaf2):
    return f"middle using {leaf2}"


@instance
def service(middle1, middle2):
    return f"{middle1} and {middle2}"


@instance
def root_obj(service):
    return f"root using {service}"
