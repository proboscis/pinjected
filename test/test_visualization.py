from pinjected import injected, Injected, design

test_design=design()
__default_design_paths__ = ['test.test_visualization.test_design']


@injected
def b(api_key,a,/):
    return a + "b" + api_key

@injected
def c(b,/):
    return b() + "c"

d:Injected = c() + "d"


__meta_design__ =design(
    overrides=design(
        a = 'some injected value'*10,
        api_key="some secret key"
    )    
)

