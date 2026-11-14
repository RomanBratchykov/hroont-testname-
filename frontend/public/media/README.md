# Mascot animations

Add `thinking.gif` here to use a separate animation while a chat request is running.
Use the same 500:650 aspect ratio and framing as `assets/Hi_soil.gif` so switching states does not move the character. A missing thinking GIF falls back to the greeting animation. Completion, errors, and Stop return the mascot to its conversation state. Reduced-motion users see the still image.

The default greeting is imported from `assets/Hi_soil.gif`. Custom mascot renderers receive idle, composing, thinking, or conversation status.

For sharper exports from After Effects, enable Continuously Rasterize for imported vector layers and render at Full resolution / Best quality. Export at least twice the largest displayed size (the current intro is up to 210 CSS pixels wide, so use at least 420 pixels of actual character width). Crop excess transparent margins consistently in both animations. GIF is raster artwork and does not preserve vector sharpness; use the original vector animation rather than upscaling an existing GIF when exporting again.

Adobe reference: https://helpx.adobe.com/ee/after-effects/desktop/work-with-layers/manage-layers/layers.html
