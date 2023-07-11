from dataclasses import dataclass
from pprint import pformat

from loguru import logger
from pinject.bindings import default_get_arg_names_from_class_name
from pinject.finding import find_classes

from pinject_design import Injected
from pinject_design.di.design import Bind


@dataclass
class DIGraphHelper:
    src: "Design"

    def get_implicit_mapping(self) -> dict[str, type]:
        from pinject_design.di.implicit_globals import IMPLICIT_BINDINGS
        classes = find_classes(self.src.modules, self.src.classes)
        for c in classes:
            for name in default_get_arg_names_from_class_name(c.__name__):
                yield name, c

    def get_explicit_mapping(self) -> dict[str, Bind]:
        return {k: b for k, b in self.src.bindings.items()}

    def total_mappings(self) -> dict[str, Injected]:
        from pinject_design.di.implicit_globals import IMPLICIT_BINDINGS
        global_implicit_mappings = IMPLICIT_BINDINGS
        logger.debug(f"global_implicit_mappings: {pformat(global_implicit_mappings)}")
        implicit_mappings = {k: Injected.bind(v) for k, v in self.get_implicit_mapping()}
        explicit_mappings = {k: bind.to_injected() for k, bind in self.get_explicit_mapping().items()}
        return {**global_implicit_mappings, **implicit_mappings, **explicit_mappings}
