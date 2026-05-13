"""Dataclass models for persistence layer. Defines Conversation and Message
dataclasses that mirror the SQLite schema and are used by the repository
layer."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Conversation:
    pass


@dataclass
class Message:
    pass
