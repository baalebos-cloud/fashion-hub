# Page-level tests

Full page render tests (mounting a page with a mocked router + auth
context) go here. Kept separate from tests/components (isolated component
units) and tests/integration (multi-step flows against a real or MSW-mocked
API) since page tests typically need the heaviest test harness setup.
