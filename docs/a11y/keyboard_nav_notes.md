# Keyboard Navigation & Screen Reader Notes

## Keyboard-Only Walkthrough (verified manually)

The reader page is fully keyboard-navigable in the following order:

1. **Tab** to textarea → type or paste text (≥50 words)
2. **Tab** to "Load demo passage" button → **Space/Enter** to load
3. **Tab** to "Render with Lume" button → **Space/Enter** to render
4. Adaptation toggles are checkboxes → **Tab** to each → **Space** to toggle
5. After render: **Tab** to reading area (focusable div with aria-label="Rendered passage")
6. **Tab** to "I'm done reading" button → **Space/Enter** to proceed
7. Comprehension radio group: **Tab** to fieldset → **Arrow keys** to select rating
8. **Tab** to "Submit" button → **Space/Enter**
9. Results panel: focusable text with reward and top-k chips
10. **Tab** to "Read another passage" button → **Space/Enter** to reset

## Focus Management

- All interactive elements use native HTML elements (button, input, label) — no div/span click handlers
- `role="group"` + heading on adaptation toggles
- `role="alert"` on error messages
- `aria-live="polite"` on loading status messages
- Loading states (rendering, submitting) disable buttons to prevent double-submit

## Screen Reader Support

- `<html lang="en">` in layout.tsx
- All sections have `aria-label`
- fieldset/legend wraps the comprehension radio group
- Each radio has an explicit `aria-label="{n} out of 5"`
- Top-k arm chips have `title` attributes with full reward data

## Automated Audit Results

- Lighthouse accessibility: **100/100** (prod build, Chrome headless)
- axe-core: **0 violations** (extracted from Lighthouse a11y data)
- See `lighthouse_root.json`, `axe.json`, `axe.txt` in this directory

## WCAG AA Color Compliance

From `apps/web/app/globals.css`:
- `--lume-overlay-warm: oklch(0.97 0.03 80)` — parchment warm background (AA against default text)
- `--lume-emphasis: oklch(0.35 0.18 25)` — emphasis color (AA on overlay AND on white)
