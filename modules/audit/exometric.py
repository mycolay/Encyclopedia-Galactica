"""Pinned adapters to existing Exometric and Manifold implementations."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PINS = {
    'lineage.py': ('C:/ai_server/Orcestr/src/orcestr/exometric/lineage.py', 'e0406ed4c0a43858505db138b069dad1f2031c26b9eab0f3e0823485d8eb3cbd'),
    'bridge.py': ('C:/ai_server/Manifold/PRODUCT/realizability_core/realizability_core/exometric_lineage_bridge.py', '85935b4be3531f0f9320ef3194d610f4b93a6c3c71ace1354434d2ba9bdc6213'),
    'independent.py': ('C:/ai_server/Manifold/PRODUCT/realizability_core/realizability_core/exometric_lineage_independent.py', '0240101e4222c553ffee4086808619af1dfb05c4c79bda6a51059229b864de5d'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open('xb') as f:
        f.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def inside(base, name):
    path = (base / name).resolve()
    path.relative_to(base.resolve())
    if Path(name).is_absolute() or str(name).startswith('artifact://'):
        raise ValueError('non_relative_path')
    return path


def checked_copy(source, target, expected=None):
    data = Path(source).read_bytes()
    if expected and hashlib.sha256(data).hexdigest() != expected.lower():
        raise ValueError('input_hash_drift: ' + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as f:
        f.write(data)


def invoke(script, args):
    result = subprocess.run([sys.executable, '-B', str(script)] + list(map(str, args)),
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError('adapter_failed: ' + result.stdout + result.stderr)
    return result.stdout.strip()


def verify_bundle(bundle, anchor):
    """Requires an independently retained anchor; never trusts the bundle's own head."""
    bundle = Path(bundle).resolve()
    anchor = read_json(anchor) if not isinstance(anchor, dict) else anchor
    if anchor.get('schema_version') != 'cosmoslov.audit_anchor.v1':
        raise ValueError('anchor_schema')
    manifest_path = bundle/'seal/exometric_lineage_manifest.json'
    if sha(manifest_path) != anchor['manifest_sha256']:
        raise ValueError('anchor_manifest_mismatch')
    manifest = read_json(manifest_path)
    if not manifest.get('artifacts') or manifest['head_chain_hash'] != anchor['head_chain_hash']:
        raise ValueError('anchor_head_mismatch')
    independent = bundle/'tools/independent.py'
    if sha(independent) != PINS['independent.py'][1]:
        raise ValueError('independent_verifier_drift')
    for e in manifest['artifacts']:
        inside(bundle, e['uri'])
    with tempfile.TemporaryDirectory(prefix='cosmoslov-verify-') as temp:
        output = Path(temp)/'recompute.json'
        invoke(independent, ['--base-dir',bundle,'--manifest',manifest_path,
            '--exometric-verification',bundle/'seal/exometric_lineage_verification.json', '--output',output])
        result = read_json(output)
    if result['head_chain_hash'] != anchor['head_chain_hash'] or result['artifact_count'] != anchor['artifact_count']:
        raise ValueError('anchor_recompute_mismatch')
    return result


def seal_run(run, bundle, anchor_path):
    run, bundle, anchor_path = Path(run).resolve(), Path(bundle).resolve(), Path(anchor_path).resolve()
    if bundle.exists() or anchor_path.exists():
        raise FileExistsError('refusing_to_overwrite_run_or_anchor')
    if anchor_path.is_relative_to(bundle):
        raise ValueError('anchor_must_be_outside_bundle')
    receipt = read_json(run/'receipt.json')
    bundle.mkdir(parents=True, exist_ok=False)
    # Preserve the original export and snapshot, checked against its receipt.
    for name, expected in dict(receipt['outputs'], **{'snapshot.db':receipt['snapshot_sha256']}).items():
        checked_copy(inside(run,name), inside(bundle,'export/'+name), expected)
    checked_copy(run/'receipt.json',bundle/'export/receipt.json')
    for name, expected in receipt['executor_files'].items():
        checked_copy(inside(ROOT,name),inside(bundle,'executor/'+name),expected)
    checked_copy(Path(__file__),bundle/'executor/modules/audit/exometric.py')
    for name in ['scripts/audit_export.py', 'tests/test_exometric_export.py', 'docs/EXOMETRIC_EXPORT_PROTOCOL_V1.md']:
        checked_copy(ROOT/name,bundle/'executor'/name)
    for name,(source,expected) in PINS.items():
        checked_copy(source,bundle/'tools'/name,expected)
    # Freeze all source texts referenced by byte-verified exported quotes, plus maps.
    cards = read_json(bundle/'export/SCI_FI_LEXICON.json')['cards']
    sources = {}
    for card in cards:
        for a in card['attestations']:
            if a['quote'] is None:
                continue
            key = a['artifact_sha256']
            target = bundle/'corpus'/key/'source.txt'
            if key not in sources:
                checked_copy(a['path'],target,key)
                checked_copy(Path(a['path']).with_name('zones.json'),target.with_name('zones.json'))
                sources[key] = str(target.relative_to(bundle)).replace('\\','/')
            zones = read_json(target.with_name('zones.json'))
            if zones.get('source_sha256') != key or not any(z.get('kind')=='body'
                and z['byte_start'] <= a['byte_start']
                and a['byte_start']+a['byte_len'] <= z['byte_end'] for z in zones.get('zones',[])):
                raise ValueError('source_zone_drift')
            data = target.read_bytes()[a['byte_start']:a['byte_start']+a['byte_len']]
            if data.decode('utf-8') != a['quote']:
                raise ValueError('export_quote_mismatch')
    write_json(bundle/'source_map.json',dict(artifact_paths=sources,
        scope='Sources and zone maps captured at sealing time; metadata does not establish scientific correctness.'))
    return seal_prepared_bundle(bundle, anchor_path)


def seal_prepared_bundle(bundle, anchor_path):
    """Seal a prepared immutable run directory using the same pinned instruments."""
    bundle, anchor_path = Path(bundle).resolve(), Path(anchor_path).resolve()
    if anchor_path.exists() or anchor_path.is_relative_to(bundle):
        raise ValueError('anchor_exists_or_inside_bundle')
    if (bundle/'seal').exists() or (bundle/'bridge_config.json').exists():
        raise FileExistsError('bundle_already_sealed_or_partial')
    for name, (_, expected) in PINS.items():
        if sha(bundle/'tools'/name) != expected:
            raise ValueError('instrument_hash_drift')
    artifacts = [dict(artifact_id=p.relative_to(bundle).as_posix(),uri=p.relative_to(bundle).as_posix())
                 for p in sorted(bundle.rglob('*')) if p.is_file()]
    config = dict(schema_version='exometric_shadow_config.v0',base_dir=str(bundle),
        runtime_path=str(bundle/'tools/lineage.py'),output_dir=str(bundle/'seal'),
        expected_runtime_sha256=PINS['lineage.py'][1],manifest_id=bundle.name,
        project_id='cosmoslov',artifacts=artifacts)
    write_json(bundle/'bridge_config.json',config)
    invoke(bundle/'tools/bridge.py',['--config',bundle/'bridge_config.json'])
    journal = read_json(bundle/'seal/exometric_adapter_journal.json')
    if journal['broad_package_initializer_loaded'] or not journal['runtime_hash_match']:
        raise ValueError('bridge_isolation_failed')
    manifest = read_json(bundle/'seal/exometric_lineage_manifest.json')
    anchor = dict(schema_version='cosmoslov.audit_anchor.v1', bundle_name=bundle.name,
        manifest_sha256=sha(bundle/'seal/exometric_lineage_manifest.json'),
        head_chain_hash=manifest['head_chain_hash'],artifact_count=manifest['artifact_count'],
        claim='integrity_only',external_custody='pending_human_retention')
    result = verify_bundle(bundle,anchor)
    write_json(bundle/'seal/independent_recompute.json',result)
    anchor_path.parent.mkdir(parents=True,exist_ok=True)
    write_json(anchor_path,anchor)
    return anchor
