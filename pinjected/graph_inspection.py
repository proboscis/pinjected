import inspect
import re
from dataclasses import dataclass
from pprint import pformat

from loguru import logger
from pinjected import Injected
from pinjected.v2.binds import IBind, BindInjected, ExprBind
from pinjected.v2.keys import IBindKey, StrBindKey, DestructorKey


def default_get_arg_names_from_class_name(class_name):
    """Converts normal class names into normal arg names.

    from github's pinject

    Normal class names are assumed to be CamelCase with an optional leading
    underscore.  Normal arg names are assumed to be lower_with_underscores.

    Args:
      class_name: a class name, e.g., "FooBar" or "_FooBar"
    Returns:
      all likely corresponding arg names, e.g., ["foo_bar"]
    """
    parts = []
    rest = class_name
    if rest.startswith('_'):
        rest = rest[1:]
    while True:
        m = re.match(r'([A-Z][a-z]+)(.*)', rest)
        if m is None:
            break
        parts.append(m.group(1))
        rest = m.group(2)
    if not parts:
        return []
    return ['_'.join(part.lower() for part in parts)]


def find_classes(modules, classes):
    if classes is not None:
        all_classes = set(classes)
    else:
        all_classes = set()
    for module in _get_explicit_or_default_modules(modules):
        # TODO(kurts): how is a module getting to be None??
        if module is not None:
            all_classes |= _find_classes_in_module(module)
    return all_classes


def _get_explicit_or_default_modules(modules):
    if modules is None:
        return []
    return modules


def _find_classes_in_module(module):
    classes = set()
    for member_name, member in inspect.getmembers(module):
        if inspect.isclass(member) and not member_name == '__class__':
            classes.add(member)
    return classes


@dataclass
class DIGraphHelper:
    src: "Design"

    def get_explicit_mapping(self) -> dict[str, IBind]:
        return {k: b for k, b in self.src.bindings.items()}

    def total_mappings(self) -> dict[str, Injected]:
        bindings = self.total_bindings()
        mappings = dict()
        for k, v in bindings.items():
            match k, v:
                case (StrBindKey(name), BindInjected(Injected() as injected)):
                    mappings[name] = injected
                case (StrBindKey(name), ExprBind(src,meta)):
                    mappings[name] = src
                case (DestructorKey(name), _):
                    pass
                case _:
                    raise ValueError(f"unsupported key type {k} and value type {v}")
        return mappings

    def total_bindings(self) -> dict[IBindKey, IBind]:
        from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
        global_implicit_mappings = IMPLICIT_BINDINGS
        # TODO add the qualified name for the global_implicit_mappings. but how?

        # logger.debug(f"global_implicit_mappings: {pformat(global_implicit_mappings)}")
        logger.debug(f"using {len(global_implicit_mappings)} global implicit mappings")
        explicit_mappings = self.get_explicit_mapping()
        return {**global_implicit_mappings, **explicit_mappings}
