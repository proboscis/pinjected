import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pinjected.v2.async_resolver import AsyncResolver
from pinjected.v2.resolver import Providable

if TYPE_CHECKING:
    from pinjected.di.design_interface import Design


@dataclass
class Resolver:
    resolver: AsyncResolver

    def provide(self, tgt: Providable):
        return asyncio.run(self.resolver.provide(tgt))

    def child_session(self, overrides: "Design"):
        return Resolver(self.resolver.child_session(overrides))

    def to_async(self):
        return self.resolver

    def __getitem__(self, item):
        return self.provide(item)

    def find_provision_errors(self, key: str):
        return asyncio.run(self.resolver.a_find_provision_errors(key))

    def check_resolution(self, key: str):
        return asyncio.run(self.resolver.a_check_resolution(key))
