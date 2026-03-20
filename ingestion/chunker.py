"""Token-aware text chunker with overlap and content hashing."""
from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass

import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    text: str
    token_count: int
    chunk_index: int
    content_hash: str


def _token_count(text: str) -> int:
    return len(_ENC.encode(text))


def chunk_text(
    text: str,
    chunk_size: int = 600,
    overlap: int = 100,
) -> list[Chunk]:
    """Split text into overlapping token-aware chunks."""
    # Split on sentences/paragraphs first
    sentences = re.split(r"(?<=[.!?])\s+|\n\n+", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0

    for sent in sentences:
        sent_tokens = _token_count(sent)
        if current_tokens + sent_tokens > chunk_size and current:
            chunk_text_str = " ".join(current)
            chunks.append(Chunk(
                text=chunk_text_str,
                token_count=_token_count(chunk_text_str),
                chunk_index=len(chunks),
                content_hash=hashlib.sha256(chunk_text_str.encode()).hexdigest(),
            ))
            # Overlap: keep last sentences that fit within overlap tokens
            overlap_sents: list[str] = []
            overlap_tokens = 0
            for s in reversed(current):
                st = _token_count(s)
                if overlap_tokens + st <= overlap:
                    overlap_sents.insert(0, s)
                    overlap_tokens += st
                else:
                    break
            current = overlap_sents
            current_tokens = overlap_tokens

        if sent_tokens > chunk_size:
            # Forcibly split oversized sentence by words
            words = sent.split()
            sub: list[str] = []
            sub_tok = 0
            for w in words:
                wt = _token_count(w)
                if sub_tok + wt > chunk_size and sub:
                    sub_str = " ".join(sub)
                    chunks.append(Chunk(
                        text=sub_str,
                        token_count=_token_count(sub_str),
                        chunk_index=len(chunks),
                        content_hash=hashlib.sha256(sub_str.encode()).hexdigest(),
                    ))
                    sub = [w]
                    sub_tok = wt
                else:
                    sub.append(w)
                    sub_tok += wt
            if sub:
                current += sub
                current_tokens += sub_tok
        else:
            current.append(sent)
            current_tokens += sent_tokens

    if current:
        chunk_text_str = " ".join(current)
        chunks.append(Chunk(
            text=chunk_text_str,
            token_count=_token_count(chunk_text_str),
            chunk_index=len(chunks),
            content_hash=hashlib.sha256(chunk_text_str.encode()).hexdigest(),
        ))

    return chunks
