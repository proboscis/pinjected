from pinjected import design

__meta_design__ = design(
    name="test_package.child.config",
    special_var="from_config_file"
)

special_config = {
    "value": "config_value",
    "source": "config.py"
}