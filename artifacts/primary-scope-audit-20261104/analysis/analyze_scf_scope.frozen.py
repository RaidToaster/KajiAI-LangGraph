"""Current-version primary-data audit of household/person conversion.

Point estimates and imputation/tie sensitivities, never sampling intervals or
a historical replication. Does not change workflow/model/scoring outcomes.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile


def weighted_cut(rows,fraction):
    """Lowest wealth fraction by household mass, with fractional boundary."""
    if not 0<fraction<=1:raise ValueError("Invalid fraction")
    if not rows or any(not math.isfinite(r["wealth"]) or not math.isfinite(r["weight"]) or r["weight"]<=0 for r in rows):raise ValueError("Invalid wealth/weight")
    ordered=sorted(rows,key=lambda r:(r["wealth"],r["id"]))
    target=fraction*math.fsum(r["weight"] for r in rows)
    taken=[];remaining=target;cutoff=None
    for row in ordered:
        weight=min(row["weight"],max(0.,remaining))
        if weight>0:taken.append((row,weight));cutoff=row["wealth"]
        remaining-=weight
        if remaining<=1e-8:break
    result={"household_mass":math.fsum(w for r,w in taken),
            "wealth_extract_units":math.fsum(r["wealth"]*w for r,w in taken),
            "household_listing_members":math.fsum(r["hh_members"]*w for r,w in taken),
            "primary_economic_unit_members":math.fsum(r["peu_members"]*w for r,w in taken),
            "proxy_2_63_members":2.63*math.fsum(w for r,w in taken),
            "wealth_cutoff_extract_units":cutoff,
            "fractional_boundary_weight":taken[-1][1] if taken[-1][1]<taken[-1][0]["weight"] else 0.,
            "topcoded_hh_mass":math.fsum(w for r,w in taken if r["hh_members"]>=12),
            "topcoded_peu_mass":math.fsum(w for r,w in taken if r["peu_members"]>=12)}
    lower=[r for r in rows if r["wealth"]<cutoff];tied=[r for r in rows if r["wealth"]==cutoff]
    tie_mass=target-math.fsum(r["weight"] for r in lower)
    sensitivity={}
    for field in ("hh_members","peu_members"):
        base=math.fsum(r[field]*r["weight"] for r in lower);bounds=[]
        for reverse in (False,True):
            left=tie_mass;values=[]
            for row in sorted(tied,key=lambda r:(r[field],r["id"]),reverse=reverse):
                weight=min(row["weight"],max(0.,left));values.append(row[field]*weight);left-=weight
                if left<=1e-8:break
            bounds.append(base+math.fsum(values))
        sensitivity[field]={"minimum":min(bounds),"maximum":max(bounds),
                            "meaning":"Allocation sensitivity among equal-wealth survey records, not a sampling interval."}
    result["tie_population_sensitivity"]=sensitivity
    return result


def main():
    import pandas as pd
    import numpy as np
    root=Path("artifacts/primary-scope-audit-20261104");data=root/"corrected-targets"
    out=root/"analysis";out.mkdir(exist_ok=False)
    protocol={"runner_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "parent_protocol_sha256":hashlib.sha256((root/"protocol.json").read_bytes()).hexdigest(),
        "data_hashes":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data.glob("*.zip")},
        "interpreter":sys.executable,"pandas":pd.__version__,"numpy":np.__version__,
        "columns":{"full":["y1","yy1","x101","x7001","x42001"],"summary":["Y1","YY1","WGT","NETWORTH"]},
        "invariants":"31240 rows/file, one-to-one Y1+YY1 join,5 implicates per case, CSV WGT=raw X42001/5, positive finite weights, documented population sizes1..12. Stop on mismatch.",
        "units":"Wealth in current extract units, declared by current source page as2025 dollars. No nominal2020 Forbes comparison is inferred.",
        "scope":"Current-version population-scope audit; no confidence intervals, independent seeds, historical-replication claim, or workflow qualification."}
    (out/"protocol.json").write_text(json.dumps(protocol,indent=2),encoding="utf8")
    with zipfile.ZipFile(data/"full-2016-stata.zip") as z:
        name=next(n for n in z.namelist() if n.endswith(".dta"))
        with z.open(name) as f:raw=pd.read_stata(f,columns=protocol["columns"]["full"],convert_categoricals=False)
    with zipfile.ZipFile(data/"summary-2016-csv.zip") as z:
        name=next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(name) as f:summary=pd.read_csv(f,usecols=protocol["columns"]["summary"])
    summary.columns=summary.columns.str.lower()
    assert len(raw)==len(summary)==31240
    frame=raw.merge(summary,on=["y1","yy1"],validate="one_to_one",how="outer",indicator=True)
    assert (frame["_merge"]=="both").all()
    assert np.allclose(frame["wgt"],frame["x42001"]/5,rtol=1e-8,atol=1e-8),"Weight convention differs from documented macro"
    assert np.isfinite(frame[["wgt","networth","x101","x7001"]].to_numpy()).all()
    assert (frame["wgt"]>0).all() and frame["x101"].between(1,12).all() and frame["x7001"].between(1,12).all()
    frame["implicate"]=(frame["y1"]-10*frame["yy1"]).astype(int)
    assert sorted(frame["implicate"].unique())==[1,2,3,4,5]
    assert (frame.groupby("yy1")["implicate"].nunique()==5).all()
    minimal=frame[["y1","yy1","implicate","wgt","x42001","networth","x101","x7001"]]
    minimal.to_csv(out/"merged-scope-fields.csv",index=False)
    def records(df,multiplier=1):
        return [{"id":int(r.y1),"wealth":float(r.networth),"weight":float(r.wgt)*multiplier,
                 "hh_members":int(r.x101),"peu_members":int(r.x7001)} for r in df.itertuples()]
    pooled=records(frame);estimates={}
    for fraction in (.37,.38):
        key=f"bottom{int(round(fraction*100))}_households"
        values=[]
        for imp,group in frame.groupby("implicate",sort=True):
            values.append({"implicate":int(imp),**weighted_cut(records(group,5),fraction)})
        fields=("household_mass","wealth_extract_units","household_listing_members","primary_economic_unit_members","proxy_2_63_members")
        estimates[key]={"pooled_implicates_weighted":weighted_cut(pooled,fraction),"per_implicate":values,
                        "mean_of_per_implicate":{field:math.fsum(v[field] for v in values)/5 for field in fields}}
    result={"row_count":len(frame),"family_count":int(frame["yy1"].nunique()),
        "total_weighted_households":float(frame["wgt"].sum()),
        "total_weighted_household_members":float((frame["wgt"]*frame["x101"]).sum()),
        "total_weighted_peu_members":float((frame["wgt"]*frame["x7001"]).sum()),
        "estimates":estimates,
        "limits":["Current public data versions are not asserted identical to the inputs used in2020.",
            "The survey's household listing and primary economic unit are distinct membership concepts, with top-coded sizes.",
            "Actual household/PEU membership does not measure individual asset allocation or independently rank individual Americans by wealth.",
            "Five implicates and boundary-tie ranges do not estimate sampling variance; replicate weights were not used.",
            "Extract dollar base is retained; no unverified currency-base substitution or automatic claim acceptance is performed."],
        "cloud_model_requests":0,"final_attempts":0,"workflow_release":False}
    (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf8")
    print(json.dumps({k:v["mean_of_per_implicate"] for k,v in estimates.items()},indent=2))


if __name__=="__main__":main()
