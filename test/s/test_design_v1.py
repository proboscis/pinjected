from returns.maybe import Some, Nothing
from returns.result import safe, Failure

from pinjected import Injected
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from pinjected.di.permissioned.blueprint import Blueprint, ResourceManifest, BindingKey, Binding, \
    RequesterManifest, Resolver, PermissionManager, ResourcePathManifest, RequesterPathManifest, binding

x_key = BindingKey("x", ResourcePathManifest(
    path="pinject_design.di.x"
))
x_bind = Binding(
    Injected.pure('resource_x'),
    manifest=RequesterPathManifest(
        path="pinject_design.di.x"
    )
)
y_key = BindingKey("y", ResourcePathManifest(
    path="pinject_design.di.y"
))
y_bind = Binding(
    Injected.bind(lambda x: x + ' resource_y'),
    manifest=RequesterPathManifest(
        path="pinject_design.di.y"
    )
)

external_manifest = RequesterPathManifest(
    path="pinject_design.external"
)


@binding
def gx():
    return 'gx'


@binding
def gy(gx, /):
    return gx() + 'y'


@binding
def gz(gx, gy, /, ):
    return gx() + gy() + 'z'


BP = Blueprint(
    bindings={
        x_key: x_bind,
        y_key: y_bind
    }
)
resolver = Resolver(
    blueprint=BP,
    permission_manager=PermissionManager()
)


def test_find_allowed_binding_key():
    assert resolver.find_allowed_binding_key('x', x_bind.manifest) == Some(x_bind)
    assert resolver.find_allowed_binding_key('y', x_bind.manifest) == Some(y_bind)
    assert resolver.find_allowed_binding_key('y', external_manifest) == Nothing


def test_find_global_default_binding_key():
    resolver.find_global_default_binding_key('x', RequesterManifest())


def test_resolve():
    assert resolver.resolve('x', x_bind.manifest) == 'resource_x'
    assert resolver.resolve('y', x_bind.manifest) == 'resource_x resource_y'
    assert resolver.resolve('gx',gx.manifest)() == 'gx'
    assert resolver.resolve('gy',gx.manifest)() == 'gxy'
    assert resolver.resolve('gz',gx.manifest)() == 'gxgxyz'
    assert isinstance(safe(resolver.resolve)('gz',x_bind.manifest),Failure)

def test_implicit_bindings():
    print(IMPLICIT_BINDINGS)