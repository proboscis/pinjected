from pinjected.helpers import ModuleVarPath
from pinjected.run_config_utils import extract_extra_codes


def test_snippet():
    #print(ModuleVarPath("pinjected.di.util.EmptyDesign").definition_snippet())
    mvp = ModuleVarPath("archpainter.style_transfer.wacv.visualizations.adain_ablation_multi_line")
    v = mvp.load()
    print(v.eval().ast)
    print(extract_extra_codes(v.eval().ast))