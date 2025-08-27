from pinjected import DesignSpec, SimpleBindSpec, design

__design__ = design(
    design_name="test_package.child.__pinjected__",
    design_var="from_design_in_pinjected_file",
    name="test_package.child.__pinjected__",
    special_var="from_pinjected_file",
    meta_name="test_package.child.__pinjected__",
    shared_key="from_design",  # Value from the original __design__
)

__design_spec__ = DesignSpec.new(
    design_var=SimpleBindSpec(
        validator=lambda item: "design_var must be str"
        if not isinstance(item, str)
        else None,
        documentation="Child module design variable",
    ),
    shared_key=SimpleBindSpec(
        validator=lambda item: "shared_key must be str"
        if not isinstance(item, str)
        else None,
        documentation="A key shared between __meta_design__ and __design__",
    ),
)

special_config = {"value": "special_config_value", "source": "__pinjected__"}
