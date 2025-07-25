from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from beartype import beartype

from pinjected import DelegatedVar, Design, EmptyDesign, Injected, design
from pinjected.di.design_spec.protocols import DesignSpec
from pinjected.module_helper import walk_module_attr, walk_module_with_special_files
from pinjected.module_inspector import ModuleVarSpec
from pinjected.module_var_path import ModuleVarPath
from pinjected.pinjected_logging import logger
from pinjected.v2.async_resolver import AsyncResolver
from pinjected.v2.keys import IBindKey, StrBindKey


def parse_pinjected_env_vars() -> dict[str, Any]:
    """Parse all PINJECTED_* environment variables into a kwargs dict."""
    import os

    env_kwargs = {}

    for env_name, env_value in os.environ.items():
        if env_name.startswith("PINJECTED_"):
            # Remove PINJECTED_ prefix and convert to lowercase
            key_name = env_name[10:].lower()  # Skip 'PINJECTED_'

            if not key_name:
                logger.warning(f"Skipping empty key from env var: {env_name}")
                continue

            env_kwargs[key_name] = env_value
            logger.debug(f"Parsed env var {env_name} -> {key_name}={env_value!r}")

    return env_kwargs


def parse_kwargs_as_design_for_env(**kwargs):
    """Parse kwargs into a design, handling {module.var} import syntax."""
    from pinjected.module_var_path import load_variable_by_module_path

    res = design()
    for k, v in kwargs.items():
        if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
            v = v[1:-1]
            loaded = load_variable_by_module_path(v)
            res += design(**{k: loaded})
        else:
            res += design(**{k: v})
    return res


@dataclass
class IdeaRunConfiguration:
    name: str
    script_path: str
    interpreter_path: str
    arguments: list[str]
    working_dir: str


@dataclass
class IdeaRunConfigurations:
    configs: dict[str, list[IdeaRunConfiguration]]


async def _a_resolve(tgt: Any | DelegatedVar | Injected):
    if isinstance(tgt, (DelegatedVar, Injected)):
        resolver = AsyncResolver(EmptyDesign)
        return await resolver.provide(tgt)
    return tgt


@dataclass
class SpecTrace:
    trace: list[ModuleVarSpec[DesignSpec]]
    accumulated: DesignSpec

    @staticmethod
    async def a_gather_from_path(file_path: Path):
        trace = []
        acc = DesignSpec.empty()
        for var in walk_module_with_special_files(
            file_path,
            attr_names=["__design_spec__"],
            special_filenames=["__pinjected__.py"],
        ):
            trace.append(var)
            assert var.var is not None
            spec: DesignSpec = await _a_resolve(var.var)
            assert isinstance(spec, DesignSpec), (
                f"Expected DesignSpec, got {type(spec)}"
            )
            acc += spec
        return SpecTrace(trace=trace, accumulated=acc)


@dataclass
class MetaContext:
    trace: list[ModuleVarSpec[Design]]
    accumulated: Design
    spec_trace: SpecTrace
    key_to_path: dict[IBindKey, str] = field(default_factory=dict)

    @staticmethod
    async def a_gather_from_path(
        file_path: Path, meta_design_name: str = "__meta_design__"
    ):
        """
        .. deprecated:: 0.3.0
           Use ``a_gather_bindings_with_legacy`` instead. This function will be removed in a future version.

        iterate through modules, for __pinjected__.py and __init__.py, looking at __meta_design__.
        but now we should look for
        __spec__ for DesignSpec,
        __design__ for Design,
        The order is __init__.py -> __pinjected__.py -> target_file.py
        """
        import warnings

        warnings.warn(
            "MetaContext.a_gather_from_path is deprecated and will be removed in a future version. "
            "Use MetaContext.a_gather_bindings_with_legacy instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        with logger.contextualize(tag="gather_meta_context"):
            from pinjected import design

            if not isinstance(file_path, Path):
                file_path = Path(file_path)
            designs = list(walk_module_attr(file_path, meta_design_name))
            designs.reverse()
            res = EmptyDesign
            overrides = EmptyDesign
            key_to_src = dict()
            for item in designs:
                logger.info(f"Added {meta_design_name} at :{item.var_path}")
                # Add migration warning for __meta_design__
                if meta_design_name == "__meta_design__":
                    logger.warning(
                        f"Use of __meta_design__ in {item.var_path} is deprecated. "
                        f"Please migrate to using __design__ in __pinjected__.py instead. "
                        f"Create a __pinjected__.py file in the same directory with a __design__ variable."
                    )
                for k, v in item.var.bindings.items():
                    logger.info(f"Binding {k} from {item.var_path}")
                logger.trace(
                    f"Current design bindings before: {res.bindings if hasattr(res, 'bindings') else 'EmptyDesign'}"
                )
                # First collect any overrides
                overrides += (
                    new_d := await AsyncResolver(item.var).provide_or(
                        "overrides", EmptyDesign
                    )
                )
                for k, v in new_d.bindings.items():
                    key_to_src[k] = item.var_path
                # Then apply the design itself to ensure its bindings (like 'name') take precedence
                res = res + item.var
                logger.trace(
                    f"Current design bindings after: {res.bindings if hasattr(res, 'bindings') else 'EmptyDesign'}"
                )
            for k, v in key_to_src.items():
                logger.debug(f"Override Key {k} from {v}")
            # Apply overrides last
            res = res + design(overrides=overrides)
            return MetaContext(
                trace=designs,
                accumulated=res,
                spec_trace=SpecTrace(trace=[], accumulated=DesignSpec.empty()),
                key_to_path=key_to_src,
            )

    @staticmethod
    async def a_gather_bindings_with_legacy(file_path):
        """
        iterate through modules, for __pinjected__.py and __init__.py, looking at __meta_design__ and __design__.
        __pinjected__.py and __design__ will override the deprecated __meta_design__ and __init__.py
        __init__.py is not recommended to avoid circular imports.
        """
        acc = EmptyDesign
        key_to_path: dict[IBindKey, str] = dict()
        trace = []
        for var in walk_module_with_special_files(
            file_path,
            attr_names=["__meta_design__", "__design__"],
            special_filenames=["__init__.py", "__pinjected__.py"],
        ):
            trace.append(var)
            ovr = EmptyDesign
            if var.var_path.endswith("__meta_design__"):
                # Raise deprecation error for __meta_design__
                raise DeprecationWarning(
                    f"Use of __meta_design__ in {var.var_path} is deprecated and no longer supported. "
                    f"Please migrate to using __design__ in __pinjected__.py file instead. "
                    f"Create a __pinjected__.py file in the same directory with a __design__ variable."
                )
                ovr = await _a_resolve(var.var)
                if StrBindKey("overrides") in var.var:
                    logger.debug(
                        "Now `overrides` are merged with `__meta_design__`. __meta_design__ and `overrides` is deprecated. use __design__ instead."
                    )
                    ovr += await AsyncResolver(var.var).provide("overrides")
            elif var.var_path.endswith("__design__"):
                ovr = await _a_resolve(var.var)

            # Extract binding locations from design metadata if available
            with logger.contextualize(tag="extract_binding_locations"):
                for k, bind in ovr.bindings.items():
                    # Try to get location from binding metadata
                    location_str = None
                    try:
                        if hasattr(bind, "metadata"):
                            # Get metadata using the property
                            metadata_maybe = bind.metadata
                            from returns.maybe import Nothing

                            if metadata_maybe != Nothing:
                                metadata = metadata_maybe.unwrap()
                                if (
                                    hasattr(metadata, "code_location")
                                    and metadata.code_location != Nothing
                                ):
                                    location = metadata.code_location.unwrap()
                                    from pinjected.di.metadata.location_data import (
                                        ModuleVarLocation,
                                    )

                                    if isinstance(location, ModuleVarLocation):
                                        location_str = (
                                            f"{location.path}:{location.line}"
                                        )
                    except Exception as e:
                        logger.debug(f"Failed to extract metadata for {k}: {e}")

                    # If no metadata location, use the file path instead of module path
                    if location_str is None:
                        # Use the actual file path which is more useful than module path
                        location_str = str(var.module_file_path)

                    key_to_path[k] = location_str
            acc += ovr

        for k, v in key_to_path.items():
            logger.debug(f"Override Key {k} from {v}")

        # Load and apply environment variables
        env_kwargs = parse_pinjected_env_vars()
        if env_kwargs:
            env_design = parse_kwargs_as_design_for_env(**env_kwargs)
            acc += env_design
            # Track env var sources in key_to_path
            for key_name in env_kwargs:
                key_to_path[StrBindKey(key_name)] = f"env:PINJECTED_{key_name.upper()}"
            logger.info(f"Applied {len(env_kwargs)} PINJECTED_* environment variables")

        spec = await SpecTrace.a_gather_from_path(file_path)

        return MetaContext(
            trace=trace, accumulated=acc, spec_trace=spec, key_to_path=key_to_path
        )

    @staticmethod
    @beartype
    def gather_from_path(file_path: Path, meta_design_name: str = "__meta_design__"):
        import asyncio

        return asyncio.run(MetaContext.a_gather_from_path(file_path, meta_design_name))

    @property
    def final_design(self):
        import asyncio

        return asyncio.run(self.a_final_design)

    @property
    async def a_final_design(self):
        with logger.contextualize(tag="design_preparation"):
            from pinjected.run_helpers.run_injected import (
                load_user_default_design,
                load_user_overrides_design,
            )

            acc = self.accumulated

            # Check for deprecated default_design_paths
            if StrBindKey("default_design_paths") in acc:
                raise DeprecationWarning(
                    "Use of 'default_design_paths' is no longer supported. "
                    "Please migrate to using __design__ in __pinjected__.py files to define your designs directly."
                )

            # Simply return the accumulated design plus user configurations
            # Note: 'overrides' is no longer a special pre-defined key, but users can still
            # have their own 'overrides' binding if they want
            return load_user_default_design() + acc + load_user_overrides_design()

    @staticmethod
    async def a_load_default_design_for_variable(var: ModuleVarPath | str):
        if isinstance(var, str):
            var = ModuleVarPath(var)
        meta_context = await MetaContext.a_gather_bindings_with_legacy(
            var.module_file_path
        )
        design = await meta_context.a_final_design
        return design

    @staticmethod
    def load_default_design_for_variable(var: ModuleVarPath | str):
        """
        .. deprecated:: 0.3.0
           Use ``a_load_default_design_for_variable`` instead. This synchronous method will be removed in a future version.
        """
        import warnings

        warnings.warn(
            "MetaContext.load_default_design_for_variable is deprecated and will be removed in a future version. "
            "Use the async version MetaContext.a_load_default_design_for_variable instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        import asyncio

        if isinstance(var, str):
            var = ModuleVarPath(var)
        return asyncio.run(MetaContext.a_load_default_design_for_variable(var))

    @staticmethod
    async def a_design_for_variable(var: ModuleVarPath | str):
        if isinstance(var, str):
            var = ModuleVarPath(var)
        design = await (
            await MetaContext.a_gather_bindings_with_legacy(var.module_file_path)
        ).a_final_design
        return design


@dataclass
class RunnablePair:
    target: Injected
    design: Design

    def run(self):
        logger.info(f"running {self.target}")
        result = self.design.to_graph()[self.target]
        logger.info(f"result: {result}")
        return result

    def save_html(self, name: str | None = None, show=True):
        if name is None:
            name = "graph.html"
        self.design.to_vis_graph().save_as_html(self.target, name, show=show)


# Removed unused import check for pydantic field_validator

__design__ = design()
