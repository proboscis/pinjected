from typing import List

from pinjected import *

StyleContentPair = object
ImageData = object


@injected
def zip_image_pairs(styles: List[ImageData], contents: List[ImageData]):
    return [StyleContentPair(s, c) for s, c in zip(styles, contents)]


wikiart_abstract_samples = {
    "synthetic_cubism": [0, 83],
    "cubism": [0, 49],
    "analytical_cubism": [5, 30],
    "pop_art": [2],
    "action_painting": [81, 51],
    "abstract_expressionism": [2],
}
wikiart_realistic_samples = {
    "romanticism": [3],
    "realism": [12],
    "post_impressionism": [0],
    "pointillism": [3],
    "northern_renaissance": [15],
    "new_realism": [4],
    "impressionism": [6],
    "fauvism": [4],
    "expressionism": [85],
    "baroque": [2]
}
imagenet_various_absolute_idx = [
    33553,  # ox, 3 cows,
    26335,  # base ball player
    13466,  # cocker spaniel (dog)
    5503,  # european gallinule (bird)
    11076,  # balloon
    38340,  # minibus
    30001,  # Granny Smith (green apple)
    29226,  # French Loaf (bread)
    44743,  # bucket
    6217,  # hay wheel
]
imagenet_various_samples: Injected = injected("imagenet_val").sample_with_indices(
    imagenet_various_absolute_idx,
    injected("image_size")
)
abstract_styles = injected("wikiart").sample_with_label_indices(wikiart_abstract_samples, injected("image_size"))
realistic_styles = injected("wikiart").sample_with_label_indices(wikiart_realistic_samples, injected("image_size"))
realistic_various_pairs: Injected = zip_image_pairs(realistic_styles, imagenet_various_samples)


def check(tgt: Injected, trace: list[tuple[str, object]] = None):
    if trace is None:
        trace = [('root', tgt)]
    from pinjected.di.app_injected import EvaledInjected
    from pinjected.di.injected import MappedInjected, MZippedInjected, InjectedPure
    import cloudpickle
    from pinjected.pinjected_logging import logger
    try:
        cloudpickle.dumps(tgt)
        return
    except Exception as e:
        trc_string = '->'.join([f'{k}' for k, v in trace])
        trc_values = '\n'.join([f'{v}' for k, v in trace])
        logger.error(f'failed to pickle {tgt} at {trc_string}. \n values:{trc_values}')

    def new_trace(name: str, value: object):
        return trace + [(name, value)]

    match tgt:
        case EvaledInjected(value, ast):
            check(value, trace=new_trace('value', value))
            check(ast, trace=new_trace('ast', ast))
        case MappedInjected(src, f):
            check(src, trace=new_trace('src', src))
            check(f, trace=new_trace('f', f))
        case MZippedInjected(srcs):
            for i, src in enumerate(srcs):
                check(src, trace=new_trace(f'srcs[{i}]', src))
        case InjectedPure(value):
            check(value, trace=new_trace('value', value))
        case _:
            raise RuntimeError(f'unknown injected type:{tgt}')


