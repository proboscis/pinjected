# Test special file at the top level

class __meta_design__:
    @staticmethod
    def provide(name):
        if name == 'special_var':
            return "from_top_level_pinjected_file"
        return None

special_config = {
    'source': '__pinjected__',
    'value': 'top_level_value'
}