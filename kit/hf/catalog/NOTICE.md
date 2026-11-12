# Vendored HyperFrames catalog components

The `*.html` files in this folder are components from the HyperFrames catalog
(https://hyperframes.heygen.com/catalog), copied from https://github.com/heygen-com/hyperframes by
`kit/hf/tools/catalog.py` on 2026-10-20.

Copyright HeyGen and the HyperFrames contributors. Licensed under the Apache License, Version 2.0
(https://www.apache.org/licenses/LICENSE-2.0). Commercial use, including monetised videos, is allowed.

Changes made when vendoring: the CDN `<script src="https://cdn.jsdelivr.net/npm/gsap@…">` tag inside each `<template>`
is removed (the host page loads the kit's own GSAP), and a one-line provenance comment is added at the top. Nothing
else is changed; a piece follows the film's look through the CSS variables the kit sets (kit/hf/core.js `HF.look`,
kit/hf/mounts.py).
