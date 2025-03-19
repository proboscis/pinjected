# Test special file at the top level

from pinjected import design

__meta_design__ = design(
    special_var="from_top_level_pinjected_file",
    meta_name="test_package.__pinjected__"
)

__design__ = design(
    design_name="test_package.__pinjected__",
    design_var="from_top_level_design"
)

special_config = {
    'source': '__pinjected__',
    'value': 'top_level_value'
}