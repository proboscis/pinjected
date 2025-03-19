from pinjected import design

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

special_config = {
    "value": "special_config_value",
    "source": "__pinjected__"
}