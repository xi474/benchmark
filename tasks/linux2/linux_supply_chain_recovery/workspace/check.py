from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
products=['content_dedup', 'version_constraints', 'provenance_merkle']
expected_checks={'content_dedup': 'f343a105d95cd415cfd21334ce1a97a921f94bc39fe5bfd583bd228d343c1f1a', 'version_constraints': 'c11406f9a37cea05b36f9cb080ffa13f6d6c84c337f3208f23acffddca181c54', 'provenance_merkle': 'b03aaa8827436ff2a7b5d7cac70e94e84aadf94efe13436a91646edf30d2076e'}
manifest=ROOT/'outputs'/'shared_manifest.json'
assert manifest.is_file(),'run materialize.py first'
row=json.loads(manifest.read_text())
assert sorted(row['products'])==sorted(products)
times={}
for name in products:
    package=ROOT/'products'/name
    check=package/'check_module.py'
    normalized=check.read_text().replace('\r\n','\n').encode()
    assert hashlib.sha256(normalized).hexdigest()==expected_checks[name],f'protected focused check changed: {name}'
    marker=package/'.focused-pass.json'
    assert marker.is_file(),f'run products/{name}/check_module.py first'
    proof=json.loads(marker.read_text())
    assert proof.get('passed') is True and proof.get('package')==name
    for rel,digest in proof['implementation_hashes'].items():
        assert hashlib.sha256((package/rel).read_bytes()).hexdigest()==digest,f'stale focused check: {name}/{rel}'
    times[name]=round(float(proof['elapsed_seconds']),3)
report={'passed':True,'products':products,'focused_check_seconds':times}
out=ROOT/'outputs'/'final_report.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print('ROOT_CHECK_PASS',json.dumps(report,sort_keys=True))
