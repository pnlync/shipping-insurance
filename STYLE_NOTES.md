# Site Style Notes

## Page Style Isolation Rule

Each page must keep its page-specific styling isolated from other pages.

Do not make a Project Memo style change by editing broad homepage selectors, and do not make a
homepage style change by editing Project Memo selectors. The same rule applies to every page pair:
Homepage, Project Memo, Project Docs, Pricing Memo, and Data & Results.

CSS is split by responsibility:

- `styles/shared.css` contains base variables, resets, global navigation, typography primitives,
  reusable link styles, and intentionally shared components.
- `styles/home.css` contains Homepage-only styles.
- `styles/project-memo.css` contains Project Memo-only styles.
- `styles/project-docs.css` contains Project Docs-only styles.
- `styles/pricing-memo.css` contains Pricing Memo-only styles.
- `styles/results.css` contains Data & Results-only styles.

Do not reintroduce a single all-page stylesheet. A page-specific request should normally edit only
that page's CSS file.

Use page-scoped wrapper classes and page-specific class prefixes for page-level layout and content
styles inside each page file. Examples:

- Homepage-specific sections should remain under homepage classes such as `.hero`,
  `.problem-section`, `.pages-section`, `.method-section`, and `.results-section`.
- Project Memo-specific sections should remain under `.executive-*`.
- Project Docs-specific sections should remain under `.docs-*`.
- Pricing Memo-specific sections should remain under `.memo-*`.
- Data & Results-specific sections should remain under result/data classes such as `.data-*`,
  `.result-*`, `.evidence-section`, `.pricing-layout`, `.segment-*`, `.tier-*`, and `.stress-*`.

Shared selectors in `styles/shared.css` should be limited to true shared primitives such as:

- CSS variables in `:root`
- base reset rules
- top navigation
- reusable links
- shared typography primitives

If `styles/shared.css` must be changed, verify every page that uses it before considering the
change complete. A page-specific request should normally add or edit page-scoped classes instead of
changing shared selectors.

When adding a new page or major redesign, create a distinct page wrapper and class prefix first.
This prevents later edits from accidentally changing unrelated pages.

## JavaScript Isolation Rule

JavaScript is also split by page responsibility:

- `scripts/plane-motion.js` is loaded only by pages that use the visual plane interaction.
- `scripts/project-memo-toc.js` is loaded only by Project Memo.

Do not put page-specific behavior into a single all-page script. If a new page needs behavior,
create a page-specific script and load it only on that page.
