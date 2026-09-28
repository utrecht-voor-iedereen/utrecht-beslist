# Contributing to Utrecht Beslist

Thanks for helping. Utrecht Beslist is a small, independent civic project, so every correction counts.

## Report a wrong summary

The fastest route is the **Report error** button on the decision page, or the
[wrong summary](https://github.com/utrecht-voor-iedereen/utrecht-beslist/issues/new?template=wrong-summary.yml)
issue form. Quote the sentence and say what the official document states instead.

## Change the code

1. Fork the repository and create a branch from `main`.
2. Set up the project as described in the [README](README.md#run-it-locally).
3. Keep the change focused, and add or update a test in `tests/` when you change behaviour.
4. Run the checks before opening a pull request:

   ```bash
   ruff check .
   mypy scripts --explicit-package-bases --ignore-missing-imports
   PYTHONPATH=. pytest tests/
   ```

5. Open a pull request that explains what was broken and why the change fixes it.

## Principles

- **Facts come from the register.** Status, dates, titles and links are copied from OpenBesluitvorming, never from the model.
- **Invent nothing.** A summary may only state amounts and dates that appear in the document.
- **Plain language.** Summaries aim at CEFR B1: short sentences, concrete words, no jargon.
- **Every language counts.** Interface text lives in `scripts/i18n.py` and `scripts/over_content.py`, in all eight languages.
- **Static and free.** No server, no tracking, no paid services.

By contributing you agree that your contribution is licensed under the [EUPL-1.2](LICENSE).
