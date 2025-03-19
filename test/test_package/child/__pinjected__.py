from pinjected import design

__meta_design__ = design(
    name="test_package.child.__pinjected__",
    special_var="from_pinjected_file"
)

special_config = {
    "value": "special_config_value",
    "source": "__pinjected__"
}