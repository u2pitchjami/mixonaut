from typing import TypeAlias, TypedDict, Union


class TrackFeatures(TypedDict):
    bpm: float
    key: str
    beat_intensity: float
    mood_emb1: float
    mood_emb2: float
    genre_emb1: float
    genre_emb2: float
    duration: float


class CandidateTrack(TrackFeatures):
    id: int


class TrackMatch(TypedDict):
    id: int
    score: float
    key: str
    reason: str
    features: CandidateTrack


# Champs métadonnées optionnels (total=False) ajoutés à TrackMatch
class EnrichedTrackMatch(TrackMatch, total=False):
    artist: str
    album: str
    title: str
    path: str


class BestCandidate(TypedDict):
    score: float
    key: str | None
    semitone: int
    transposed_bpm: float | None
    pitch_shift: float


TranspositionDict = dict[str, str | float]
TrackMatchList = list[TrackMatch]


GroupedTrackMatches = dict[str, TrackMatchList]
MatchResult = Union[TrackMatchList, GroupedTrackMatches]
TranspoCombo: TypeAlias = BestCandidate

EnrichedTrackMatchList = list[EnrichedTrackMatch]
GroupedEnrichedMatches = dict[str, EnrichedTrackMatchList]
MarkdownInput = EnrichedTrackMatchList | GroupedEnrichedMatches
