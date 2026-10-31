"""Pure offline scoring helpers; no network or API client is used."""
import re
import string

def normalize(text):
    text = str(text).lower().translate(str.maketrans('', '', string.punctuation))
    return ' '.join(re.sub(r'\b(a|an|the)\b', ' ', text).split())

def grade(record):
    choices = (record.get('response') or {}).get('choices') or []
    message = choices[0].get('message', {}) if choices else {}
    text = message.get('content') or ''
    matches = list(re.finditer(r'FINAL\s+ANSWER\s*:\s*', text, re.I))
    if matches:
        answer = text[matches[-1].end():].strip().split('\n')[0].strip(' *`"')
    else:
        answer = text.strip() if '\n' not in text.strip() and len(text.split()) <= 30 else None
    aliases = record['answers']
    exact = any(normalize(answer) == normalize(a) for a in aliases) if answer is not None else False
    contains = any(normalize(a) in normalize(text) for a in aliases)
    finish = choices[0].get('finish_reason') if choices else None
    return {
        'text': text,
        'reasoning_text': message.get('reasoning_content'),
        'extracted_answer': answer,
        'final_marker_present': bool(matches),
        'exact_match': exact if record['status'] == 'ok' else None,
        'answer_substring': contains if record['status'] == 'ok' else None,
        'finish_reason': finish,
        'truncated': finish == 'length',
        'needs_review': record['status'] == 'ok' and (answer is None or contains != exact or finish == 'length'),
        'output_words': len(text.split()),
        'output_characters': len(text),
    }

def strategy_scope(prompt_id):
    if prompt_id.startswith('ChineseCoT'):
        return 'translation_needs_review'
    if prompt_id in ['OnlyNumbers', 'WordLimit(1)', 'CharLimit(10)', 'TokenLimit(10)']:
        return 'answer_budget_stress'
    if prompt_id in ['NoSpaces', 'NoProperGrammar', 'AbbreviateWords']:
        return 'format_stress'
    return 'main_comparison'
