import importlib
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"evaluation"))
cut=importlib.import_module("analyze_scf_scope").weighted_cut


def row(id,w,value,hh,peu=None):
    return dict(id=id,weight=w,wealth=value,hh_members=hh,peu_members=hh if peu is None else peu)


def test_fractional_household_boundary_preserves_person_counts():
    result=cut([row(1,1,-10,2),row(2,3,10,4)],.5)
    assert result["household_mass"]==2 and result["wealth_extract_units"]==0
    assert result["household_listing_members"]==6 and result["fractional_boundary_weight"]==1


def test_five_implicates_do_not_multiply_the_population():
    original=[row(1,1,-10,2),row(2,3,10,4)]
    repeated=[row(imp*10+r["id"],r["weight"]/5,r["wealth"],r["hh_members"]) for imp in range(5) for r in original]
    assert math.isclose(cut(repeated,.5)["household_mass"],2)
    assert math.isclose(cut(repeated,.5)["household_listing_members"],6)


def test_negative37_and_positive38_remain_distinct():
    records=[row(1,37,-44/37,2),row(2,1,50,4),row(3,62,1000,1)]
    assert math.isclose(cut(records,.37)["wealth_extract_units"],-44)
    assert math.isclose(cut(records,.38)["wealth_extract_units"],6)
    assert cut(records,.38)["household_listing_members"]==78


def test_equal_wealth_ties_report_membership_allocation_sensitivity():
    result=cut([row(1,1,0,1),row(2,1,0,5)],.5)
    bounds=result["tie_population_sensitivity"]["hh_members"]
    assert bounds["minimum"]==1 and bounds["maximum"]==5
