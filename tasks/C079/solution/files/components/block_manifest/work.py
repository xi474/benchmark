def compute(p):
 data=bytes.fromhex(p['file_hex']);n=p['chunk_size'];return ([['thumbnail',0,p['thumbnail_hex']]] if p.get('thumbnail_hex') is not None else [])+[['file',i//n,data[i:i+n].hex()] for i in range(0,len(data),n)]
