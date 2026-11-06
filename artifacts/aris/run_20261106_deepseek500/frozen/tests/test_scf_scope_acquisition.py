import importlib
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"evaluation"))
select=importlib.import_module("scf_scope_acquire_v2").select_main_targets


def test_duplicate_stata_labels_do_not_select_replicate_weights():
    html='''<a href="/econres/files/scf2016s.zip">Stata version (10 MB ZIP)</a>
    <a href="/econres/files/scf2016rw1s.zip">Stata version (36 MB ZIP)</a>
    <a href="/econres/files/scfp2016excel.zip">CSV extract data (4 MB ZIP)</a>'''
    targets=select(html)
    assert targets["full-2016-stata.zip"].endswith("/scf2016s.zip")
    assert all("rw1" not in url for url in targets.values())
