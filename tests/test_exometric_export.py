import hashlib
import json
import shutil
from pathlib import Path
import pytest
from modules.audit.exometric import seal_run, verify_bundle, write_json, sha


@pytest.fixture
def sealed(tmp_path):
    run=tmp_path/'run';run.mkdir()
    (run/'snapshot.db').write_bytes(b'test snapshot bytes')
    (run/'SCI_FI_LEXICON.json').write_text(json.dumps({'cards':[]}),encoding='utf-8')
    (run/'SCI_FI_LEXICON.md').write_text('Test export',encoding='utf-8')
    write_json(run/'receipt.json',dict(outputs={n:sha(run/n) for n in ['SCI_FI_LEXICON.json','SCI_FI_LEXICON.md']},
        snapshot_sha256=sha(run/'snapshot.db'),executor_files={}))
    bundle=tmp_path/'bundle';anchor=tmp_path/'anchor.json'
    seal_run(run,bundle,anchor)
    return run,bundle,anchor


def test_clean_and_portable(sealed,tmp_path):
    _,bundle,anchor=sealed
    result=verify_bundle(bundle,anchor)
    assert result['verdict']=='PASS' and result['imports_exometric'] is False
    relocated=tmp_path/'relocated'
    shutil.copytree(bundle,relocated)
    assert verify_bundle(relocated,anchor)['verdict']=='PASS'


def test_content_tamper(sealed):
    _,bundle,anchor=sealed
    (bundle/'export/SCI_FI_LEXICON.md').write_text('tampered')
    with pytest.raises(ValueError,match='adapter_failed'):
        verify_bundle(bundle,anchor)


def test_self_consistent_truncation(sealed):
    _,bundle,anchor=sealed
    p=bundle/'seal/exometric_lineage_manifest.json'
    manifest=json.loads(p.read_text())
    manifest['artifacts'].pop()
    manifest['artifact_count']=len(manifest['artifacts'])
    manifest['head_chain_hash']=manifest['artifacts'][-1]['chain_hash']
    p.write_text(json.dumps(manifest))
    p=bundle/'seal/exometric_lineage_verification.json'
    v=json.loads(p.read_text());v['artifact_count']=manifest['artifact_count'];v['head_chain_hash']=manifest['head_chain_hash']
    p.write_text(json.dumps(v))
    with pytest.raises(ValueError,match='anchor_manifest_mismatch'):
        verify_bundle(bundle,anchor)


def test_manifest_reorder(sealed):
    _,bundle,anchor=sealed
    p=bundle/'seal/exometric_lineage_manifest.json';m=json.loads(p.read_text())
    m['artifacts'].reverse();p.write_text(json.dumps(m))
    with pytest.raises(ValueError): verify_bundle(bundle,anchor)


def test_no_overwrite_and_wrong_anchor(sealed):
    run,bundle,anchor=sealed
    before=sha(anchor)
    with pytest.raises(FileExistsError): seal_run(run,bundle,anchor)
    assert sha(anchor)==before
    a=json.loads(anchor.read_text());a['head_chain_hash']='0'*64
    with pytest.raises(ValueError,match='anchor_head_mismatch'): verify_bundle(bundle,a)


def test_reject_path_escape(tmp_path):
    from modules.audit.exometric import inside
    with pytest.raises(ValueError): inside(tmp_path,'../escaped')


def test_pin_drift(sealed):
    _,bundle,anchor=sealed
    (bundle/'tools/independent.py').write_text('raise RuntimeError("should never run")')
    with pytest.raises(ValueError,match='independent_verifier_drift'): verify_bundle(bundle,anchor)
