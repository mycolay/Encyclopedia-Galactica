"""Conservative source alignment; does not validate entity meaning."""
import hashlib
import re


def locate(text, quote):
    """Allow whitespace changes only, returning a unique original byte span."""
    if not isinstance(quote, str) or not quote.strip():
        return None, 'empty_quote'
    parts = re.split(r'(\s+)', quote.strip())
    pattern = ''.join(r'\s+' if p.isspace() else re.escape(p) for p in parts)
    matches = list(re.finditer('(?=(' + pattern + '))', text))
    if len(matches) != 1:
        return None, 'quote_absent' if not matches else 'quote_ambiguous'
    start, end = matches[0].span(1)
    raw = text[start:end]
    return dict(local_byte_start=len(text[:start].encode('utf-8')),
        byte_len=len(raw.encode('utf-8')), quote_original=raw,
        quote_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        alignment='exact' if raw == quote else 'whitespace_only'), None


def check_entity(item, scene):
    issues = []
    evidence, error = locate(scene['text'], item.get('quote'))
    if error:
        issues.append(error)
    name = item.get('name')
    if not isinstance(name, str) or not name.strip():
        issues.append('missing_name')
    else:
        pattern = r'(?<!\w)' + r'\s+'.join(re.escape(x) for x in name.split()) + r'(?!\w)'
        if not re.search(pattern, scene['text']):
            issues.append('name_not_in_original')
        if evidence and not re.search(pattern, evidence['quote_original']):
            issues.append('name_not_in_evidence')
    if item.get('kind') not in ('concept', 'character', 'place'):
        issues.append('unknown_category')
    if item.get('epistemic') not in ('explicit', 'inferred'):
        issues.append('unknown_epistemic_status')
    if not isinstance(item.get('description_uk'), str) or not item['description_uk'].strip():
        issues.append('missing_description')
    if evidence:
        evidence['byte_start'] = scene['byte_start'] + evidence.pop('local_byte_start')
    return dict(issues=issues, evidence=evidence,
        status='held' if issues else 'source_grounded_editorial_pending',
        semantic_validation=False)
