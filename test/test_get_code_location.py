from pinjected import design, Design, Injected
from pinjected.ide_supports.create_configs import design_metadata
from pinjected.v2.async_resolver import AsyncResolver

test_design = design(
    c=1,
    a=Injected.bind(lambda: 0),
    b=Injected.bind(lambda: 1)
)


def test_get_location():
    (AsyncResolver(test_design + design(
        default_design_paths=[
            "test.test_get_code_location.test_design"
        ]
    ))).to_blocking()[design_metadata]
