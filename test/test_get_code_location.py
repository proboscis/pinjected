from pinjected import instances, providers, classes, Design
from pinjected.ide_supports.create_configs import design_metadata

design = instances(
    c=1
) + providers(
    a=lambda: 0,
    b=lambda: 1
)
def test_get_location():
    (design+instances(
        default_design_paths=[
            "test.test_get_code_location.design"
        ]
    )).to_resolver().to_blocking()[design_metadata]