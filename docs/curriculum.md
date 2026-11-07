# Curriculum and recital repertoire

Practice scope includes staff reading, hands-together coordination, the circle of fourths/fifths, major and minor triads, natural/harmonic minor and accidentals, four-note chords, arpeggios, and two-hand parallel/contrary-motion scale patterns. These are separate technique targets with explicit progress; songs are **application contexts**, not prerequisites or proof of mastery.

## Reading-first instruction and teaching attribution

**Primary learning objective:** becoming fluent at reading the printed grand staff
and translating unfamiliar notation into keyboard actions, rather than recognizing
memorized exercise patterns or only guessing note names on a watch. A genuine
reading check should conceal note-name and highlighted-key hints until after
the first played MIDI answer; see [reading-first practice](reading.md).

**Teacher acknowledgement:** piano teacher **Shirly Mann** has contributed
instructional guidance on some of the user's practice techniques and method-book
selections, including a reminder to use a *little comfortable wrist movement
on chords* rather than playing with a locked wrist. This is an acknowledgement of
lessons and learning influences, not an assertion that the teacher wrote,
approved or endorsed this software. Chord technique is self/teacher-observed:
MIDI event data cannot evaluate wrist motion, finger mechanics, or discomfort.

## Method-book checkpoints

- **Alfred's Basic Adult Piano Course — Level One**: reference only; the user's physical or licensed score is authoritative for pages, pacing, notation, and drills.
- **Level Two**: subsequent practice context; do not automatically assume Level One is completed.
- Capture optional book/exercise/page *identifiers* in private practice notes. Feedback/v2 supports `--method-book-id` and `--method-checkpoint`, bound to the approved practice date/timezone and local revision. Never reproduce protected exercises, scores, or scans in the public catalog.

## Recital candidates

| ID | Piece | Status | Technique references | Source |
| --- | --- | --- | --- | --- |
| `fur-elise` | Für Elise | Candidate, not qualified | Reading, coordination, minor | User's arrangement/edition unspecified |
| `over-the-rainbow` | Over the Rainbow | Candidate, not qualified | Reading, coordination, triads | User's Alfred Level One reference |
| `jacobs-ladder` | Jacob's Ladder | Candidate, not qualified | Reading, coordination, triads | Arrangement unspecified |

The three titles are examples, not prescribed repertoire. Their publication/arrangement rights differ. Store only metadata and user-authored section observations; do not copy score material from the method books.

## Proposed use in a session

1. One primary technique, e.g. `reading`, with a small playable exercise.
2. Short reading from the user's legitimate Alfred score or an original MusicXML exercise produced by `pianoctl notation`.
3. Optional application to a *section* of one recital candidate, with the section ID or page reference saved privately.
4. Report physical comfort, musical accuracy, reading accuracy, and whether hands were actually used as intended. MIDI pitch/timing alone cannot verify visual reading or which hand played.
5. The deterministic planner and explicit approval gates select next work from reviewed evidence; books and songs never silently promote a technique.

The reference catalog in [`catalogs/curriculum.json`](../catalogs/curriculum.json) defines these IDs. Book and recital completion status remain unknown until reported. 


## Added arpeggio and personalized scale curriculum

Two arpeggio exercises are now independent focus targets:

- `arpeggio-major-one-octave`: name C-E-G and ascend/descend one octave with relaxed thumb transfer.
- `arpeggio-major-minor-two-octaves`: compare C major and A minor broken chords across two octaves. Both are original exercises, not licensed Alfred notation.

For two-hand scale coordination, `scale-crossings-two-octaves` begins on LH C3 / RH C4 and travels up two C-major octaves in parallel. The player's reported left-hand crossing cues are attached to LH A3 (finger **3**, first octave) and LH D4 (finger **4**, second octave). These represent *the user's technique reference*, not a MIDI-observed finger movement or universal prescribed fingering.

`scale-five-phase-opposing` now models the **clarified** five-phase motion as five contiguous two-hand spans. No phase uses an LH rest:

| Phase | Left-hand path (illustrative) | Right-hand path (illustrative) | Motion |
| --- | --- | --- | --- |
| 1 | C3 → C4 | C4 → C5 | Both ascend one octave |
| 2 | C4 → C3 → C4 | C5 → C6 → C5 | Contrary outward, **both return** |
| 3 | C4 → C5 → C4 | C5 → C6 → C5 | Parallel up, **both return** |
| 4 | C4 → C3 → C4 | C5 → C6 → C5 | Contrary outward, **both return** |
| 5 | C4 → C3 | C5 → C4 | Both descend one octave |

The relative motion and return behavior follow the player's correction. **LH C3 / RH C4 are still illustrative starting octaves**, not user-confirmed physical registers. The machine-readable `onset-groups/v1` realization uses 57 contiguous two-hand onsets, explicit phases, and no inferred fingering cues for this five-phase exercise. The **independent** `scale-crossings-two-octaves` drill retains the player-reported LH finger 3 on A3 / finger 4 on D4. Neither cue verifies an actual finger motion. Nothing from the user-owned Alfred books is reproduced.

**Technique gate:** MIDI may evaluate event timing, intended note groups and synchronization; only a reviewed self-check can establish hand identity, finger crossing, posture, tension and meaningful scale reading.
