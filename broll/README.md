# B-roll library

His own reusable clips: him walking into a café, sitting with the laptop, typing, poses, places, screens. Any future
video can cut to them. The media and the catalog are local only (git-ignored); this README is the only tracked file.

**Add a clip** (it's copied in untouched, at source quality):

    uv run python kit/broll.py add ~/Downloads/IMG_0297.MOV --cat=me --tags=cafe,laptop,night,leaning-back \
        --note="leans back while the agent works" --use=0.4-12.5 --from=not-ai-made

**Find clips** for a moment in a new video:

    uv run python kit/broll.py find --tags=cafe,laptop
    uv run python kit/broll.py find --text=walking

**Look at everything:** open `broll/sheet.jpg`. It has three frames of every clip, with its id, tags and notes.

**Rules:**
- **Categories:**
  - me: him on camera;
  - hands: typing, phone, writing;
  - screens: a screen filmed with the camera;
  - places: a room, street or café with nobody in it;
  - objects;
  - motion: walking, driving, a door;
  - misc.
- **Tags:** short and lowercase. Name where it is, what he's doing, the time of day and the mood, e.g. `cafe, laptop, night, walking-in, smiling`.
- **`--use`:** the usable seconds (skip the shaky start or someone walking through). Use several ranges if needed: `--use=0.5-6,9-14`.
- **`--people=others`:** set it when anyone else is in frame. Reusing the clip then needs a tracked blur (kit/reel/hide.py) unless they agreed.
- **HDR clips** (iPhone HLG) are marked HDR. A film tone-maps them like any take (kit/film/tonemap.py).
- **Copies, not moves:** the original stays where it was. Delete it from Downloads only once it's here.
