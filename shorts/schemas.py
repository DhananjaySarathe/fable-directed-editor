"""The analysis a take produces (`shorts analyze` -> analysis.json), as pydantic models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Word(BaseModel):
    i: int
    text: str
    start: float
    end: float
    p: float = 1.0
    aligned: bool = True
    start_gap: bool = False     # a real quiet stretch (>= 30 ms) comes right before the word
    end_gap: bool = False       # a real quiet stretch comes right after the word


class Sentence(BaseModel):
    id: str
    first: int
    last: int
    text: str
    start: float
    end: float


class Pause(BaseModel):
    after: int
    start: float
    end: float
    duration: float


class Loudness(BaseModel):
    integrated: float | None = None
    lra: float | None = None
    true_peak: float | None = None


class FaceBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class TimeRange(BaseModel):
    start: float
    end: float


class Picture(BaseModel):
    fps: float
    face_presence: float
    face_box: FaceBox | None = None
    face_track: list[list[float] | None] = []
    blurry: list[TimeRange] = []
    dark: list[TimeRange] = []
    no_face: list[TimeRange] = []
    scene_changes: list[float] = []


class SourceInfo(BaseModel):
    path: str
    working_path: str
    duration: float
    fps: int
    frames: int
    width: int
    height: int
    normalized: bool


class Analysis(BaseModel):
    version: Literal[1] = 1
    source: SourceInfo
    language: str
    words: list[Word]
    sentences: list[Sentence]
    pauses: list[Pause]
    speech_db: float
    floor_db: float
    quiet_db: float
    dip_db: float
    loudness: Loudness
    picture: Picture
    contact_sheet: str
    warnings: list[str] = []
