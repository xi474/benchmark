from functools import lru_cache

def best_match(ions,peaks,tolerance):
    @lru_cache(None)
    def search(index,used):
        if index==len(ions):return (0,0,0)
        best=search(index+1,used)
        for peak_index,peak in enumerate(peaks):
            if used>>peak_index&1 or abs(ions[index]-peak["mass"])>tolerance:continue
            tail=search(index+1,used|1<<peak_index)
            option=(tail[0]+1,tail[1]+peak["intensity"],tail[2]-abs(ions[index]-peak["mass"]))
            if option>best:best=option
        return best
    return search(0,0)
