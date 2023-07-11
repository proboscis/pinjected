import inspect
import platform
import uuid
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from pprint import pformat
from typing import Callable, List, Any, Dict, Union

import networkx as nx
from cytoolz import memoize
from loguru import logger

from pampy import match
from returns.pipeline import is_successful
from returns.result import safe, Result, Failure

from pinject_design.di.design import PinjectBind, Bind, InjectedProvider
from pinject_design.di.injected import Injected, InjectedFunction, InjectedPure, MappedInjected, \
    ZippedInjected, MZippedInjected, InjectedByName, extract_dependency, InjectedWithDefaultDesign, \
    PartialInjectedFunction
from pinject_design.di.util import Design, DirectPinjectProvider, PinjectProviderBind
from pinject_design.exceptions import DependencyResolutionFailure, _MissingDepsError
from pinject_design.graph_inspection import DIGraphHelper
from pinject_design.nx_graph_util import NxGraphUtil


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

    def new_name(self, base: str):
        return f"{base}_{str(uuid.uuid4())[:6]}"

    def __post_init__(self):
        self.src = self.src.bind_instance(session='DummyForVisualization').build()
        self.helper = DIGraphHelper(self.src)
        self.implicit_mappings = dict(self.helper.get_implicit_mapping())
        self.pinject_mappings = dict(self._get_configured())
        # we want to know if the binding is InjectedProvider or not
        self.explicit_mappings: Dict[str, Injected] = {k: b.to_injected() for k, b in self.src.bindings.items() if
                                                       k not in self.pinject_mappings}
        self.explicit_mappings.update(**self.helper.total_mappings())
        self.multi_mappings = {k: b for k, b in self.src.multi_binds.items()}

        self.direct_injected = dict()
        self.injected_to_id = dict()

        @memoize
        def deps_impl(src: str):
            if "provide_" in src:
                src = src.replace("provide_", "")
            if src in self.explicit_mappings:
                em = self.explicit_mappings[src]
                return self.resolve_injected(em)
                # if isinstance(em, InjectedProvider):
                #     return self.resolve_injected(em.src)
                # else:
                #     return em.to_injected().dependencies()
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
        "give new name to unknown manual injected values and return dependencies"
        # i needs to be hashable
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
            lambda e: getitem(self.explicit_mappings, key)
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

    def di_dfs(self, src, replace_missing=False):
        ignore_list = ["mzip_src_", "mapped_src_", "injected_kwargs_"]

        def filter(node):
            res = any([ignore in node for ignore in ignore_list])
            if res:
                logger.info(f"ignore {node}")
            return res

        def dfs(prev, current, trace=[]):
            assert current not in trace[:-1], f"cycle detected! trace:{trace}, current:{current}"
            try:
                nexts: List[str] = self.dependencies_of(current)
            except Exception as e:
                import traceback
                trb = traceback.format_exc()
                if replace_missing:
                    logger.warning(f"failed to get neighbors of {current} at {' => '.join(trace)}. due to {e} \n{trb}")
                    nexts = []
                else:
                    raise _MissingDepsError(f"failed to get neighbors of {current} at {' => '.join(trace)}.", current,
                                            trace) from e
            for n in nexts:
                match (filter(current), filter(n)):
                    case (True, True):
                        yield from dfs(prev, n, trace + [n])
                    case (True, False):
                        yield prev, n, trace
                        yield from dfs(prev, n, trace + [n])
                    case (False, True):
                        yield from dfs(current, n, trace + [n])
                    case (False, False):
                        yield current, n, trace
                        yield from dfs(current, n, trace + [n])

        yield from dfs(src, src, [src])

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

    def get_source(self, f):
        try:
            if hasattr(f, "__original_file__"):
                file = f.__original_file__
            else:
                file = inspect.getfile(f)
            if hasattr(f, "__original_code__"):
                src = f.__original_code__
            else:
                src = inspect.getsource(f)
            res = file + "\n" + src

        except Exception as e:
            from loguru import logger
            logger.warning(f"{repr(e)[:100]} error from {repr(f)[:100]}")
            res = f"failed:{f} from {f}"

        res = res.replace("<", "").replace(">", "")
        from loguru import logger
        res = res.replace("\t", "....").replace(" ", ".")
        # logger.info(f"extracted sources:\n{res}")
        return res

    def parse_injected(self, tgt: Injected):
        # from archpainter.my_artifacts.artifact_object import IArtifactObject
        match tgt:
            case InjectedWithDefaultDesign(src, default_design):
                return self.parse_injected(src)
            case InjectedFunction(f):
                desc = f"Injected:{safe(getattr)(f, '__name__').value_or(repr(f))}"
                return ("injected", desc, self.get_source(f))
            case InjectedPure(v):
                desc = f"Pure:{v}"
                return ("injected", desc, self.get_source(v) if isinstance(v, Callable) else str(v))
            case PartialInjectedFunction(InjectedFunction(src)):
                desc = f"partial=>{src.__name__}"
                return ("injected", desc, self.get_source(src))
            case PartialInjectedFunction(src):
                desc = f"partial=>{src}"
                return ("injected", desc, self.get_source(src))
            case MappedInjected(src, mapping) as mi:
                desc = f"{mi.__class__.__name__}"
                return ("injected", desc, self.get_source(mapping))
            case ZippedInjected(srcs) as zi:
                desc = f"{zi.__class__.__name__}"
                return ("injected", desc, "zipped")
            case MZippedInjected(srcs) as mzi:
                desc = f"{mzi.__class__.__name__}"
                return ("injected", desc, "mzipped")
            case InjectedByName(name):
                desc = f"{name}"
                return ("injected", desc, "by_name")
            case Injected() as injected:
                desc = f"{injected.__class__.__name__}"
                return ("injected", desc, str(injected))
        #
        # return match(tgt,
        #              InjectedWithDefaultDesign, lambda iwdd: self.parse_injected(iwdd.src),
        #              InjectedFunction,
        #              lambda injected: ("injected",
        #                                f"Injected:{safe(getattr)(injected.target_function, '__name__').value_or(repr(injected.target_function))}",
        #                                self.get_source(injected.target_function)),
        #              InjectedPure,
        #              lambda injected: (
        #                  "injected",
        #                  f"Pure:{injected.value}",
        #                  self.get_source(injected.value)
        #                  if isinstance(injected, Callable)
        #                  else str(injected.value)
        #              ),
        #              PartialInjectedFunction,
        #              lambda injected: ("injected", f"partial=>{injected.src.target_function.__name__}",
        #                                self.get_source(injected.src.target_function)),
        #              MappedInjected,
        #              lambda injected: ("injected", f"{injected.__class__.__name__}", self.get_source(injected.f)),
        #              ZippedInjected,
        #              lambda injected: ("injected", f"{injected.__class__.__name__}", "zipped"),
        #              MZippedInjected,
        #              lambda injected: ("injected", f"{injected.__class__.__name__}", "mzipped"),
        #              # IArtifactObject,
        #              # lambda injected: ("injected", f"artifact:{injected.metadata.identifier}", str(injected)),
        #              InjectedByName,
        #              lambda injected: (
        #                  "injected", f"name:{injected.name}", f"injected by name:{injected.name}"),
        #              Injected,
        #              lambda injected: ("injected", f"{injected.__class__.__name__}", str(injected)),
        #              )

    def create_dependency_digraph_rooted(self, root: Injected, root_name="__root__",
                                         replace_missing=True
                                         ) -> NxGraphUtil:
        tmp_design = self.src.bind_provider(**{root_name: root})
        return DIGraph(tmp_design) \
            .create_dependency_digraph(
            root_name,
            replace_missing=replace_missing
        )

    def create_graph_from_nodes(self, nodes: List[str], replace_missing=True):
        from loguru import logger
        logger.info(f"making dependency graph for {nodes}.")
        nx_graph = nx.DiGraph()
        # why am I seeing no deps?
        for node in nodes:
            nx_graph.add_node(node)
            for a, b, trc in self.di_dfs(node, replace_missing=replace_missing):
                nx_graph.add_edge(b, a)
        self.stylize_graph(nx_graph, replace_missing=replace_missing)
        return NxGraphUtil(nx_graph)

    def get_node_to_sl(self, nx_graph, replace_missing):
        @memoize
        def node_to_sl(n):
            def parse(tgt):
                return match(tgt,
                             Injected, self.parse_injected,
                             InjectedProvider(Injected), self.parse_injected,
                             PinjectProviderBind, lambda ppb: ("function", ppb.f.__name__, self.get_source(ppb.f)),
                             DirectPinjectProvider,
                             lambda dpp: ("method", dpp.method.__name__, self.get_source(dpp.method)),
                             PinjectBind({"to_instance": callable}), lambda i: ("instance", str(i), self.get_source(i)),
                             PinjectBind({"to_instance": Any}),
                             lambda i: ("instance", str(i), f"instance:{pformat(i)}"),
                             PinjectBind({"to_class": Any}), lambda i: ("class", i.__name__, self.get_source(i)),
                             type, lambda cls: ("class", cls.__name__, self.get_source(cls)),
                             list, lambda providers: ("multi_binding", repr(providers), repr(providers)),
                             # MetaBind, lambda mb: (mb.metadata["src"],parse(mb.src)[1],mb.metadata["src"]),
                             Any, lambda a: ("unknown", str(a), f"unknown-type:{type(a)}=>{a}")
                             )

            if replace_missing and not is_successful(safe(self.__getitem__)(n)):
                group, short, long = "missing", f"missing_{n}", f"missing_{n}"
            else:
                group, short, long = parse(self[n])
            short = str(short).replace("<", "").replace(">", "")[:100]
            n_edges = len(list(nx_graph.neighbors(n))) + safe(self.dependencies_of)(n).map(len).value_or(0)
            return dict(
                label=f"{n}\n{short}",
                title=long,
                group=group,
                value=n_edges,
                mass=n_edges * 0.5 + 1,
            )

        return node_to_sl

    def stylize_graph(self, nx_graph, replace_missing):
        node_to_sl = self.get_node_to_sl(nx_graph, replace_missing)
        for n in nx_graph.nodes:
            assert isinstance(n, str)
            attrs = node_to_sl(n)
            node = nx_graph.nodes[n]
            for k, v in attrs.items():
                node[k] = v
        return nx_graph

    def create_dependency_digraph(self, roots: Union[str, List[str]], replace_missing=True) -> NxGraphUtil:
        if isinstance(roots, str):
            roots = [roots]
        # hmm,
        from loguru import logger
        logger.info(f"making dependency graph for {roots}.")
        nx_graph = nx.DiGraph()
        # why am I seeing no deps?
        for root in roots:
            for a, b, trc in self.di_dfs(root, replace_missing=replace_missing):
                nx_graph.add_edge(b, a)
            nx_graph.add_node(root)

        self.stylize_graph(nx_graph, replace_missing)

        for root in roots:
            nx_graph.nodes[root]["group"] = "root"
        return NxGraphUtil(nx_graph)

    def create_dependency_network(self, roots: Union[str, List[str]], replace_missing=True):
        nx_graph = self.create_dependency_digraph(roots, replace_missing)
        return nx_graph.to_physics_network()

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

    def save_as_html(self, tgt: Injected, name: str, visualize_missing=True, show=True):
        nx = self.create_dependency_digraph_rooted(tgt, replace_missing=visualize_missing)
        nx.save_as_html(name, show=show)

    def plot(self, roots: Union[str, List[str]], visualize_missing=True):
        if "darwin" in platform.system().lower():
            G = self.create_dependency_digraph(roots, replace_missing=visualize_missing)
            G.plot_mpl()
        else:
            from loguru import logger
            logger.warning("visualization of a design is disabled for non mac os.")

    def show_html(self, roots, visualize_missing=True):
        g = self.create_dependency_digraph(roots, replace_missing=visualize_missing)
        g.show_html()

    def show_injected_html(self, tgt: Injected, name: str = None):
        assert isinstance(tgt, Injected)
        assert platform.system().lower() == "darwin"
        nx_graph = self.create_dependency_digraph_rooted(tgt, name or "__root__", replace_missing=True)
        nx_graph.show_html_temp()


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
