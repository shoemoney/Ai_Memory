# Blind test for the trained-tools study

`oot2-v1.1.jsonl`: 120 user requests (80 need one or two of the eight commands, 40 need none), written from the command descriptions alone by an author who did not see the training data, the training templates or any earlier test. It was fixed before the second adapter's training data was compared with it. Original work for this project, CC0.

SHA-256: `8debdb545301bdb48c7271579c9f6cdc921b0cc5547750141e8cec13dba87b4b`

Fields: `id`, `request`, `commands` (expected command names in order, empty when none is needed), `category`, `note`.

## Versions

The file published here is v1.1. The original (v1, SHA-256 `cf13fa71d5c824e5dda2d421a596f16fbc655d84696b1cfb903e81de27c4041e`) named real places, organisations, teams and retailers and used web domains that might belong to real sites. v1.1 replaces those 23 strings with invented names of similar length and kind and moves every domain under the reserved `.example` domain. No request was reworded and no label changed; the substitution table was fixed before it was applied and before any model was scored on v1.1.

The first blind results in this study (second adapter 76 of 80 first commands) were measured on v1; later results are on v1.1 and say so. The v1 file, the substitution table and the per-request traces of the v1 runs are not published; their summaries are, and the rest is available on request.
