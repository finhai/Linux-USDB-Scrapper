# Player-compatible export

The user selected VERSION 1.0.0 with AUDIO only on 2026-10-22, superseding the
previous draft-v2 target. The released UltraStar Deluxe 2026.10.0 parser accepts
AUDIO for version 1.x and explicitly rejects version 2.0.0:
https://github.com/UltraStar-Deluxe/USDX/blob/v2026.10.0/src/base/USong.pas

Downloads use serialize_v1_txt. BPM, timing headers and the note block stay
unchanged; AUDIO/VIDEO/COVER refer to local files. Output is UTF-8, without the
obsolete source ENCODING declaration. Legacy duet singer labels become P1/P2.
Ambiguous legacy timing extensions and v2 input fail rather than silently changing
playback. The draft-v2 API remains available for explicit research/tests but is
not used by the download worker.

Existing v2 downloads are not automatically rewritten. Download them again from
USDB to regenerate from original timing. Do not merely change their VERSION tag.
Parser-source compatibility and automated fidelity tests are not a substitute
for real playback validation, which remains outstanding.
