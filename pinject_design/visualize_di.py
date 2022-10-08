import inspect
import uuid
from dataclasses import dataclass
from itertools import chain
from pprint import pformat
from typing import Callable, List, Any, Dict, Union

import networkx as nx
from cytoolz import memoize
from loguru import logger
from pampy import match
from pinject.bindings import default_get_arg_names_from_class_name
from pinject.finding import find_classes
from pyvis.network import Network
from returns.result import safe, Result, Failure

from pinject_design.di.design import PinjectBind, Bind, InjectedProvider
from pinject_design.di.injected import Injected, InjectedFunction, InjectedPure, MappedInjected, \
    ZippedInjected, MZippedInjected, InjectedByName, extract_dependency
from pinject_design.di.util import Design, DirectPinjectProvider, PinjectProviderBind
from pinject_design.exceptions import DependencyResolutionFailure, _MissingDepsError


def dfs(neighbors: Callable, node: str, trace=[]):
    nexts: List[str] = neighbors(node)
    for n in nexts:
        yield node, n, trace
        yield from dfs(neighbors, n, trace + [n])


safe_attr = safe(getattr)


@safe
def getitem(tgt, name):
    return tgt[name]


# %%
@dataclass
class PinProvider:
    src: Callable

    def __post_init__(self):
        # self.arg_binding_keys:Result = safe_attr(self.src, "_pinject_arg_binding_keys")
        self.non_injectables: Result = safe_attr(self.src, "_pinject_non_injectables")
        # self.orig_f:Result = safe_attr(self.src, "_pinject_orig_fn")
        # self.provider_decorations:Result = safe_attr(self.src, "_pinject_provider_decorations")


@dataclass
class DIGraph:
    src: Design

    def _get_configured(self):
        for k, b in self.src.bindings.items():
            if isinstance(b, DirectPinjectProvider) and hasattr(b.method, "_pinject_is_wrapper"):
                pp = PinProvider(b.method)
                yield k, pp

    def _get_mapping(self):
        classes = find_classes(self.src.modules, self.src.classes)
        for c in classes:
            for name in default_get_arg_names_from_class_name(c.__name__):
                yield name, c

    def new_name(self, base: str):
        return f"{base}_{str(uuid.uuid4())[:6]}"

    def __post_init__(self):
        self.src = self.src.build()
        self.implicit_mappings = dict(self._get_mapping())
        self.pinject_mappings = dict(self._get_configured())
        # we want to know if the binding is InjectedProvider or not
        self.explicit_mappings: Dict[str, Bind] = {k: b for k, b in self.src.bindings.items() if
                                                   k not in self.pinject_mappings}
        self.multi_mappings = {k: b for k, b in self.src.multi_binds.items()}

        self.direct_injected = dict()
        self.injected_to_id = dict()

        @memoize
        def deps_impl(src: str):
            if "provide_" in src:
                src = src.replace("provide_", "")
            if src in self.explicit_mappings:
                em = self.explicit_mappings[src]
                if isinstance(em, InjectedProvider):
                    return self.resolve_injected(em.src)
                else:
                    return em.to_injected().dependencies()
            elif src in self.implicit_mappings:
                return Injected.bind(self.implicit_mappings[src]).dependencies()
            elif src in self.pinject_mappings:
                pp: PinProvider = self.pinject_mappings[src]
                deps = [d for d in Injected.bind(pp.src).dependencies() if
                        d not in pp.non_injectables.value_or([])]
                return deps
            elif src in self.multi_mappings:
                return list(set(chain(*[Injected.bind(tgt).dependencies() for tgt in self.multi_mappings[src]])))
            elif src in self.direct_injected:
                di = self.direct_injected[src]
                return self.resolve_injected(di)
            else:
                raise RuntimeError(f"key not found!:{src}")

        self.deps_impl = deps_impl

    def resolve_injected(self, i: Injected) -> List[str]:
        "give new name to unknown manual injected valus and return dependencies"
        if i not in self.injected_to_id:
            self.injected_to_id[i] = str(uuid.uuid4())[:6]
            # logger.info(f"add injected node:\n{tabulate.tabulate(list(self.injected_to_id.items()))}")
        #        else:
        #            assert False
        _id = self.injected_to_id[i]
        if isinstance(i, InjectedFunction):
            deps = []
            for k, v in i.kwargs_mapping.items():
                dep_name = f"{k}_{_id}"
                injected = match(v,
                                 str, Injected.by_name,
                                 type, Injected.bind,
                                 callable, Injected.bind,
                                 Injected, lambda i: i
                                 )
                self.direct_injected[dep_name] = injected

                # logger.info(f"add direct injected node:\n{tabulate.tabulate(list(self.direct_injected.items()))}")
                deps.append(dep_name)
            missings = list(sum([list(extract_dependency(m)) for m in i.missings], []))
            return deps + list(missings)
        elif isinstance(i, MappedInjected):
            dep_name = self.new_name("mapped_src")
            # dep_name = f"mapped_injected_src_{str(uuid.uuid4())[:6]}"
            self.direct_injected[dep_name] = i.src
            return [dep_name]
        elif isinstance(i, ZippedInjected):
            a = self.new_name("zipped_src_a")
            b = self.new_name("zipped_src_b")
            self.direct_injected[a] = i.a
            self.direct_injected[b] = i.b
            return [a, b]
        elif isinstance(i, MZippedInjected):
            res = []
            for k, src in enumerate(i.srcs):
                sn = self.new_name(f"mzip_src_{k}")
                self.direct_injected[sn] = src
                res.append(sn)
            return res
        else:
            return list(i.dependencies())

    def __getitem__(self, key):
        if "provide_" in key:
            key = key.replace("provide_", "")
        item = getitem(
            self.src.bindings, key
        ).lash(
            lambda e: getitem(self.implicit_mappings, key)
        ).lash(
            lambda e: getitem(self.pinject_mappings, key)
        ).lash(
            lambda e: getitem(self.multi_mappings, key)
        ).lash(
            lambda e: getitem(self.direct_injected, key)
        )
        if isinstance(item, Failure):
            raise KeyError(f"{key} is not found in design!")
        return item.unwrap()

    def dependencies_of(self, src):
        return self.deps_impl(src)

    def di_dfs(self, src):
        def dfs(node: str, trace=[]):
            try:
                nexts: List[str] = self.dependencies_of(node)
            except Exception as e:
                raise _MissingDepsError(f"failed to get neighbors of {node} at {' => '.join(trace)}.", node,
                                        trace) from e
            for n in nexts:
                yield node, n, trace
                yield from dfs(n, trace + [n])

        yield from dfs(src, [src])

    def di_dfs_validation(self, src):
        def dfs(node: str, trace=[]):
            nexts = []
            try:
                nexts: List[str] = self.dependencies_of(node)
            except Exception as e:
                yield DependencyResolutionFailure(node, trace, e)
            for n in nexts:
                yield from dfs(n, trace + [n])

        yield from dfs(src, [src])

    def create_dependency_network(self, roots: Union[str, List[str]]):
        if isinstance(roots, str):
            roots = [roots]

        def get_source(f):
            try:
                file = inspect.getfile(f)
                src = inspect.getsource(f)
                res = file + "\n" + src

            except Exception as e:
                logger.warning(f"{e} error from {f}")
                res = f"failed:{f} from {f}"

            res = res.replace("<", "").replace(">", "")
            return res

        # get_source = lambda f: safe(inspect.getsource)(f).value_or(f"failed:{f}").replace("<", "").replace(">", "")

        nx_graph = nx.DiGraph()
        for root in roots:
            for a, b, trc in self.di_dfs(root):
                nx_graph.add_edge(b, a)

        @memoize
        def node_to_sl(n):
            def parse(tgt):
                return match(tgt,
                             Injected, parse_injected,
                             InjectedProvider(Injected), parse_injected,
                             PinjectProviderBind, lambda ppb: ("function", ppb.f.__name__, get_source(ppb.f)),
                             DirectPinjectProvider, lambda dpp: ("method", dpp.method.__name__, get_source(dpp.method)),
                             PinjectBind({"to_instance": callable}), lambda i: ("instance", str(i), get_source(i)),
                             PinjectBind({"to_instance": Any}),
                             lambda i: ("instance", str(i), f"instance:{pformat(i)}"),
                             PinjectBind({"to_class": Any}), lambda i: ("class", i.__name__, get_source(i)),
                             type, lambda cls: ("class", cls.__name__, get_source(cls)),
                             list, lambda providers: ("multi_binding", repr(providers), repr(providers)),
                             # MetaBind, lambda mb: (mb.metadata["src"],parse(mb.src)[1],mb.metadata["src"]),
                             Any, lambda a: ("unknown", str(a), f"unknown-type:{type(a)}=>{a}")
                             )

            def parse_injected(tgt: Injected):
                # from archpainter.my_artifacts.artifact_object import IArtifactObject
                return match(tgt,
                             InjectedFunction,
                             lambda injected: ("injected",
                                               f"Injected:{safe(getattr)(injected.target_function, '__name__').value_or(repr(injected.target_function))}",
                                               get_source(injected.target_function)),
                             InjectedPure,
                             lambda injected: (
                                 "injected",
                                 f"Pure:{injected.value}",
                                 get_source(injected.value)
                                 if isinstance(injected, Callable)
                                 else str(injected.value)
                             ),
                             MappedInjected,
                             lambda injected: ("injected", f"{injected.__class__.__name__}", get_source(injected.f)),
                             ZippedInjected,
                             lambda injected: ("injected", f"{injected.__class__.__name__}", "zipped"),
                             MZippedInjected,
                             lambda injected: ("injected", f"{injected.__class__.__name__}", "mzipped"),
                             # IArtifactObject,
                             # lambda injected: ("injected", f"artifact:{injected.metadata.identifier}", str(injected)),
                             InjectedByName,
                             lambda injected: (
                                 "injected", f"name:{injected.name}", f"injected by name:{injected.name}"),
                             Injected,
                             lambda injected: ("injected", f"{injected.__class__.__name__}", str(injected)),
                             )

            group, short, long = parse(self[n])
            short = str(short).replace("<", "").replace(">", "")[:100]
            # long = long.replace("\n", "<br>")  # .replace("<","").replace(">","")

            # logger.debug(short)
            # logger.debug(long)
            n_edges = len(list(nx_graph.neighbors(n))) + len(self.dependencies_of(n))
            return dict(
                label=f"{n}\n{short}",
                title=long,
                group=group,
                value=n_edges,
                mass=n_edges * 0.5 + 1,
            )

        for root in roots:
            nx_graph.add_node(root)
        for n in nx_graph.nodes:
            assert isinstance(n, str)
            attrs = node_to_sl(n)
            node = nx_graph.nodes[n]
            for k, v in attrs.items():
                node[k] = v
        for root in roots:
            nx_graph.nodes[root]["group"] = "root"

        nt = Network('100%', '100%', directed=True)
        nt.from_nx(nx_graph)
        nt.show_buttons(filter_=["physics"])
        nt.toggle_physics(True)
        return nt

    def find_missing_dependencies(self, roots: Union[str, List[str]]) -> List[DependencyResolutionFailure]:
        if isinstance(roots, str):
            roots = [roots]
        failures = []
        for r in roots:
            failures += self.di_dfs_validation(r)
        return failures

    def show_graph_notebook(self, roots: Union[str, List[str]]):
        nt = self.create_dependency_network(roots)
        nt.width = 1000
        nt.height = 1000
        nt.prep_notebook()
        return nt.show("__notebook__.html")

    def save_as_html(self, roots: Union[str, List[str]], dst_path: str):
        nt = self.create_dependency_network(roots)
        nt.show(dst_path)


# %%
def create_dependency_graph(d: Design, roots: List[str], output_file="dependencies.html"):
    dig = DIGraph(d.bind_instance(
        job_type="net_visualization"
    ))
    nt = dig.create_dependency_network(roots)
    nt.show(output_file)
    return nt

# %%
# import os
#
# d = find_cfg_by_alias("ceylon").exp_design()
# create_dependency_graph(d, "rgb_to_xyz_training", "out.html")
#
# os.system("open out.html")
