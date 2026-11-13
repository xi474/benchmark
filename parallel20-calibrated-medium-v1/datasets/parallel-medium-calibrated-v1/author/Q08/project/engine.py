from .digest import enumerate_candidates
from .score import best_match

def evaluate(data):
    candidates=enumerate_candidates(data["proteins"],data["modifications"])
    winners=[]
    for spectrum in data["spectra"]:
        best=None
        for candidate in candidates:
            score=best_match(candidate["ions"],spectrum["peaks"],data["tolerance"])
            key=(-score[0],-score[1],-score[2],candidate["kind"]!="target",candidate["id"])
            if best is None or key<best[0]:best=(key,candidate,score)
        _,candidate,score=best
        winners.append({"spectrum":spectrum["id"],"candidate":candidate["id"],"kind":candidate["kind"],"score":list(score)})
    winners.sort(key=lambda row:(-row["score"][0],-row["score"][1],-row["score"][2],row["spectrum"]))
    target_count=decoy_count=0
    for row in winners:
        if row["kind"]=="target":target_count+=1
        else:decoy_count+=1
        row["fdr_numerator"]=decoy_count
        row["fdr_denominator"]=max(1,target_count)
    return {"candidate_count":len(candidates),"winners":winners}
