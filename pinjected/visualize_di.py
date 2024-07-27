import inspect
import platform
import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Union

import networkx as nx
from cytoolz import memoize
from loguru import logger
from returns.pipeline import is_successful
from returns.result import safe, Failure

from pinjected.di.app_injected import EvaledInjected
from pinjected.di.expr_util import show_expr
from pinjected.di.injected import Injected, InjectedFunction, InjectedPure, MappedInjected, \
    ZippedInjected, MZippedInjected, InjectedByName, extract_dependency, InjectedWithDefaultDesign, \
    PartialInjectedFunction
from pinjected.di.proxiable import DelegatedVar
from pinjected.exceptions import DependencyResolutionFailure, _MissingDepsError, CyclicDependency
from pinjected.graph_inspection import DIGraphHelper
from pinjected.module_var_path import ModuleVarPath
from pinjected.nx_graph_util import NxGraphUtil
from pinjected.providable import Providable
from pinjected.v2.binds import BindInjected


def dfs(neighbors: Callable, node: str, trace=[]):
    nexts: List[str] = neighbors(node)
    for n in nexts:
        yield node, n, trace
        yield from dfs(neighbors, n, trace + [n])


safe_attr = safe(getattr)


@safe
def getitem(tgt, name):
    return tgt[name]


import colorsys


def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb


def get_color(n_edges):
    h = (1.0 - max(0, min(10, n_edges)) / 10.0) * 0.67  # 0.67 is the hue for blue in the HSV color system.
    rgb = [int(x * 255) for x in
           colorsys.hsv_to_rgb(h, 1.0, 1.0)]  # convert hsv color (h,1,1) to rgb then multiply by 255
    return rgb_to_hex(tuple(rgb))


class MissingKeyError(RuntimeError):
    pass

@dataclass
class DIGraph:
    src: "Design"

    def new_name(self, base: str):
        return f"{base}_{str(uuid.uuid4())[:6]}"

    def __post_init__(self):
        self.helper = DIGraphHelper(self.src)
        self.explicit_mappings: dict[str, Injected] = self.helper.total_mappings()

        self.direct_injected = dict()
        self.injected_to_id = dict()

        @memoize
        def deps_impl(src: str):
            if "provide_" in src:
                src = src.replace("provide_", "")
            if src in self.explicit_mappings:
                em = self.explicit_mappings[src]
                return self.resolve_injected(em)
            elif src in self.direct_injected:
                di = self.direct_injected[src]
                return self.resolve_injected(di)
            else:
                raise MissingKeyError(f"DI key not found!:{src}")

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
                match v:
                    case str():
                        injected = Injected.by_name(v)
                    case type():
                        injected = Injected.bind(v)
                    case Injected():
                        injected = v
                    case f if callable(f):
                        injected = Injected.bind(f)
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
            return list(i.complete_dependencies)

    def __getitem__(self, key):
        if "provide_" in key:
            key = key.replace("provide_", "")
        item = getitem(
            self.src.bindings, key
        ).lash(
            lambda e: getitem(self.explicit_mappings, key)
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
                    logger.info(f"failed to get neighbors of {current} at {' => '.join(trace)}. due to {e}")
                    # logger.warning(f"failed to get neighbors of {current} at {' => '.join(trace)}. due to {e} \n{trb}")
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
            # logger.info(f"dfs:{node},{trace}")
            nexts = []
            try:
                nexts: List[str] = self.dependencies_of(node)
            except MissingKeyError as e:
                yield DependencyResolutionFailure(node, trace, e)
            for n in nexts:
                if n in trace:
                    yield CyclicDependency(n, trace)
                else:
                    yield from dfs(n, trace + [n])

        yield from dfs(src, [src])

    def distilled(self, tgt: Providable) -> "Design":
        from pinjected import providers
        from pinjected import Design
        match tgt:
            case str():
                deps = set([t[1] for t in self.di_dfs(tgt)])
                nodes = set([t[0] for t in self.di_dfs(tgt)])
                distilled = Design.from_bindings(
                    {k: self.src[k] for k in deps | nodes}
                )
                return distilled

            case _:
                from pinjected.di.graph import providable_to_injected
                _injected = providable_to_injected(tgt)
                tmp_design = self.src + providers(
                    __target__=_injected
                )
                return tmp_design.to_vis_graph().distilled("__target__")

    @staticmethod
    def get_source(f):
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
        return res

    @staticmethod
    def get_source_repr(f):
        res = DIGraph.get_source(f)

        res = res.replace("<", "").replace(">", "")
        res = res.replace("\t", "....").replace(" ", ".")
        # logger.info(f"extracted sources:\n{res}")
        return res

    def parse_injected(self, tgt: Injected):
        # from archpainter.my_artifacts.artifact_object import IArtifactObject
        match tgt:
            case InjectedWithDefaultDesign(src, default_design):
                return self.parse_injected(src)
            case InjectedFunction(f) as _if:
                try:
                    desc = f"Injected:{safe(getattr)(_if.original_function, '__name__').value_or(repr(f))}"
                except Exception as e:
                    logger.error(f"failed to get func info from {f} due to {e}")
                    raise e
                return ("injected", desc, self.get_source_repr(f))
            case InjectedPure(v):
                desc = f"Pure:{v}"
                return ("injected", desc, self.get_source_repr(v) if isinstance(v, Callable) else str(v))
            case PartialInjectedFunction(InjectedFunction(src)):
                desc = f"partial=>{src.__name__}"
                return ("injected", desc, self.get_source_repr(src))
            case PartialInjectedFunction(src):
                desc = f"partial=>{src}"
                return ("injected", desc, self.get_source_repr(src))
            case MappedInjected(src, mapping) as mi:
                desc = f"{mi.__class__.__name__}"
                return ("injected", desc, self.get_source_repr(mapping))
            case ZippedInjected(srcs) as zi:
                desc = f"{zi.__class__.__name__}"
                return ("injected", desc, "zipped")
            case MZippedInjected(srcs) as mzi:
                desc = f"{mzi.__class__.__name__}"
                return ("injected", desc, "mzipped")
            case InjectedByName(name):
                desc = f"{name}"
                return ("injected", desc, "by_name")
            case EvaledInjected(val, ast):
                expr = show_expr(ast)
                desc = f"Eval({expr})"
                return ("injected", desc, expr)
            case Injected() as injected:
                desc = f"{injected.__class__.__name__}"
                return ("injected", desc, str(injected))
            case unknown:
                raise ValueError(f"unknown injected type {unknown}")

    def create_dependency_digraph_rooted(self, root: Injected, root_name="__root__",
                                         replace_missing=True
                                         ) -> NxGraphUtil:
        from pinjected import providers
        tmp_design = self.src + providers(**{root_name: root})
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
                match tgt:
                    case Injected():
                        return self.parse_injected(tgt)
                    case BindInjected(tgt, _):
                        return self.parse_injected(tgt)
                    case cls if isinstance(cls, type):
                        return ("class", cls.__name__, self.get_source_repr(cls))
                    case [*providers]:
                        return ("multi_binding", repr(providers), repr(providers))
                    case _:
                        return ("unknown", repr(tgt), repr(tgt))

            if replace_missing and not is_successful(safe(self.__getitem__)(n)):
                group, short, long = "missing", f"missing_{n}", f"missing_{n}"
            else:
                group, short, long = parse(self[n])
            short = str(short).replace("<", "").replace(">", "")[:100]
            n_edges = len(list(nx_graph.neighbors(n))) + safe(self.dependencies_of)(n).map(len).value_or(0)

            return dict(
                label=f"{n}\n{short}",
                title=long,
                value=n_edges,
                mass=n_edges * 0.5 + 1,
                color=get_color(n_edges),
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

    def to_python_script(self,
                         root: Union[str, ModuleVarPath, Injected],
                         design_path: Union[str, ModuleVarPath]
                         ):
        # we assume that __target__ is already added to this design...
        graph = defaultdict(list)
        match root:
            case (Injected() | DelegatedVar()):
                tgt = Injected.ensure_injected(root)
                root_path = ModuleVarPath("__dummy__.root")
            case str():
                root_path = ModuleVarPath(root)
                tgt = Injected.ensure_injected(root_path.load())
            case ModuleVarPath():
                root_path = root
                tgt = Injected.ensure_injected(root_path.load())
            case _:
                raise ValueError(f"unsupported type for root:{root}")

        if not isinstance(design_path, ModuleVarPath):
            design_path = ModuleVarPath(design_path)
        script = f"""
from pinjected.di.util import Design,providers
{design_path.to_import_line()} # Please correct this line as needed
{root_path.to_import_line()} # Please correct this line as needed
d:Design = {design_path.var_name} + providers(
    __target__= {root_path.var_name}
)
g = d.to_graph()
"""
        for dep in tgt.dependencies():
            graph["__target__"].append(dep)
            for a, b, trc in self.di_dfs(dep, replace_missing=True):
                graph[a].append(b)

        written = set()

        def resolve_node(node, args):
            match (node, args):
                case _, [] if node in self.explicit_mappings:
                    tgt = self.explicit_mappings[node]
                    match tgt:
                        case InjectedPure(str(value)):
                            return f"{node} = \"{value}\"\n"
                        case InjectedPure(value):
                            return f"{node} = {value}\n"
            args = ", ".join(set(args))
            return f"{node} = g['{node}']({args})\n"

        def dfs_write(node):
            nonlocal script
            if node in written:
                return
            deps = graph[node]
            for m in deps:
                dfs_write(m)
            script += resolve_node(node, deps)
            written.add(node)

        dfs_write("__target__")
        return script

    def create_dependency_digraph(self,
                                  roots: Union[str, List[str]],
                                  replace_missing=True,
                                  root_group='root',
                                  ignore_nodes: List[str] = None
                                  ) -> NxGraphUtil:
        ignore_nodes = set(ignore_nodes or [])
        if isinstance(roots, str):
            roots = [roots]
        # hmm,
        from loguru import logger
        logger.info(f"making dependency graph for {roots}.")
        nx_graph = nx.DiGraph()
        # why am I seeing no deps?
        for root in roots:
            for a, b, trc in self.di_dfs(root, replace_missing=replace_missing):
                if a not in ignore_nodes and b not in ignore_nodes:
                    nx_graph.add_edge(b, a)
            if root not in ignore_nodes:
                nx_graph.add_node(root)

        self.stylize_graph(nx_graph, replace_missing)

        if root_group:
            for root in roots:
                nx_graph.nodes[root]["group"] = root_group
        return NxGraphUtil(nx_graph)

    def create_dependency_network(self,
                                  roots: Union[str, List[str]],
                                  replace_missing=True,
                                  ignore_nodes: List[str] = None
                                  ):
        nx_graph = self.create_dependency_digraph(
            roots,
            replace_missing,
            ignore_nodes=ignore_nodes
        )
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

    def save_as_html(self, tgt: Injected, dst_root: Path, visualize_missing=True, show=True):
        nx = self.create_dependency_digraph_rooted(tgt, replace_missing=visualize_missing)
        #nx.save_as_html(name, show=show)
        return nx.save_as_html_at(dst_root)



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
        tgt = Injected.ensure_injected(tgt)
        assert isinstance(tgt, Injected)
        nx_graph = self.create_dependency_digraph_rooted(tgt, name or "__root__", replace_missing=True)
        nx_graph.show_html_temp()

    def show_whole_html(self):
        roots = list(self.explicit_mappings.keys())
        self.create_dependency_digraph(roots, replace_missing=True, root_group=None).show_html_temp()


def create_dependency_graph(d: "Design", roots: List[str], output_file="dependencies.html"):
    from pinjected import instances
    dig = DIGraph(d + instances(
        job_type="net_visualization"
    ))
    nt = dig.create_dependency_network(roots)
    nt.show(output_file)
    return nt
