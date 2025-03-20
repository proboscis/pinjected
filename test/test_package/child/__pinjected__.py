from pinjected import design, DesignSpec, SimpleBindSpec

__meta_design__ = design(
    name="test_package.child.__pinjected__",
    special_var="from_pinjected_file",
    meta_name="test_package.child.__pinjected__",
    shared_key="from_meta_design"
)

__design__ = design(
    design_name="test_package.child.__pinjected__",
    design_var="from_design_in_pinjected_file",
    shared_key="from_design"  # This should override the value from __meta_design__
)

__design_spec__ = DesignSpec.new(
    design_var=SimpleBindSpec(
        validator=lambda item: "design_var must be str" if not isinstance(item, str) else None,
        documentation="Child module design variable"
    ),
    shared_key=SimpleBindSpec(
        validator=lambda item: "shared_key must be str" if not isinstance(item, str) else None,
        documentation="A key shared between __meta_design__ and __design__"
    )
)

special_config = {
    "value": "special_config_value",
    "source": "__pinjected__"
}