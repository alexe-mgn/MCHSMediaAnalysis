from typing import *
import os

import spacy.lang.ru
import spacy.cli
import spacy.tokens
import spacy.matcher
import spacy

import utils

from . import proc_config

__all__ = ["NLP", "MCHSTextProcessor"]

# NLP = spacy.load("ru_core_news_sm")
if os.path.isdir(utils.PATH.SPACY_MODEL):
    NLP = spacy.load(utils.PATH.SPACY_MODEL)
else:
    try:
        import ru_core_news_sm

        NLP = ru_core_news_sm.load()
    except ImportError:
        spacy.cli.download("ru_core_news_sm")
        NLP = spacy.load("ru_core_news_sm")

_pattern_matcher = spacy.matcher.Matcher(NLP.vocab)
for key, ps in proc_config.PATTERNS.items():
    _pattern_matcher.add(key, ps)


@spacy.Language.component("pattern_entity_tagger")
def pattern_tag_entities(doc: spacy.tokens.Doc, matcher: spacy.matcher.Matcher = _pattern_matcher):
    old_entities = list(doc.ents)
    new_entities = []
    for m_id, start, end in matcher(doc):
        span = spacy.tokens.Span(doc, start, end, label=matcher.vocab.strings[m_id])
        for entity in old_entities[:]:
            if entity.start < span.end and entity.end > span.start:
                old_entities.remove(entity)
        for entity in new_entities[:]:
            if entity.start < span.end and entity.end > span.start:
                span = span if (span.end - span.start) >= (entity.end - entity.start) else entity
                new_entities.remove(entity)
        new_entities.append(span)
    doc.set_ents(old_entities + new_entities)
    return doc


NLP.add_pipe("pattern_entity_tagger", last=True)


class MCHSTextProcessor:

    def __init__(self, text: str, nlp: spacy.Language = NLP):
        self._nlp = nlp
        self.doc = self._nlp(text)

    def process(self):
        doc = self.doc
        news_type = self._extract_type(doc)
        news = self._extract_entities(doc)
        news['type'] = news_type
        return news

    @staticmethod
    def _extract_type(doc: spacy.tokens.Doc):
        lemma: str = doc[:].lemma_
        news_type = None
        type_score = 0
        for i, kws in proc_config.KEYWORDS.items():
            score = 0
            for kw in kws:
                score += lemma.count(kw)
            if score > type_score:
                news_type = i
                type_score = score
        return news_type

    @staticmethod
    def _process_name(span: spacy.tokens.Span):
        name = []
        for w in span:
            if w.pos_ == "PROPN":
                if name and name[-1] != '-':
                    name.append(' ')
                name.append(w.lemma_)
            elif w.text == '-':
                name.append('-')
            elif name:
                break
        return ''.join(name)

    @staticmethod
    def _process_count(span: spacy.tokens.Span) -> Optional[float]:
        nw = ('ноль', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять')
        for w in span:
            try:
                return float(w.text.replace(',', '.'))
            except ValueError:
                pass
            if w.lemma_ in nw:
                return float(nw.index(w.lemma_))
        return None

    @classmethod
    def _extract_entities(cls, doc: spacy.tokens.Doc) -> Dict[str, Any]:
        entities = {}
        for entity in doc.ents:
            entity: spacy.tokens.Span
            label = entity.label_
            if label == 'region':
                entities[label] = entity.lemma_
            elif label == 'city' or label == 'water':
                entities[label] = cls._process_name(entity)
            elif label == 'injuries':
                if (n := cls._process_count(entity)) is not None:
                    entities[label] = entities.get(label, 0) + round(n)
                else:
                    entities[label] = max(entities.get(label, 0), int('не' not in entity.lemma_))
            elif label == 'n_staff' or label == 'n_tech':
                entities[label] = max(entities.get(label, 0),
                                      n if (n := cls._process_count(entity)) is not None else 1)
            elif label == 'area':
                if (n := cls._process_count(entity)) is not None:
                    if 'кило' in entity.lemma_:
                        n *= 10 ** 6
                    elif 'га' in entity.lemma_ or 'гектар' in entity.lemma_:
                        n *= 10 ** 4
                    entities[label] = round(n)
            elif label == 'LOC' and \
                    'city' not in entities and \
                    'region' not in entities and \
                    len(entity) == 1 and entity.lemma_ != 'россия':
                entities['city'] = entity.lemma_
        return entities
