# Test special file at the top level

from pinjected import design, DesignSpec, SimpleBindSpec

__meta_design__ = design(
    special_var="from_top_level_pinjected_file",
    meta_name="test_package.__pinjected__"
)

__design__ = design(
    design_name="test_package.__pinjected__",
    design_var="from_top_level_design"
)

__design_spec__ = DesignSpec.new(
    design_name=SimpleBindSpec(
        validator = lambda item: "design_name must be str" if not isinstance(item, str) else None,
        documentation="This is a test design spec"
    )
)


special_config = {
    'source': '__pinjected__',
    'value': 'top_level_value'
}