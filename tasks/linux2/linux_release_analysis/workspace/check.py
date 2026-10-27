from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
products=['dependency_impact', 'policy_precedence', 'event_windows']
expected_checks={'dependency_impact': 'd312ee82cec4c746e454b75cff838dd25ee84aeeea0ed823b5c04199c7dc96b2', 'policy_precedence': '27469863a88f5ea417a9c7294bc4b4a2939b1adaa83ce939d98536bf524e1fe5', 'event_windows': '60315a91209213d95c112eaaa2ad8219eb615620db2bcf1e2c53cd8675bbcf21'}
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
