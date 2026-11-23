<!--
PR title must follow Conventional Commits, e.g.
  feat(reports): add a supplier ageing report
  fix(vat): exclude settlement entries
-->

### What does this PR do?

<!-- Explain the change and the problem it solves. -->

### Type of change

- [ ] Bug fix
- [ ] New report or feature
- [ ] Refactor / tech debt
- [ ] Docs / CI only

### Checklist

- [ ] PR title follows Conventional Commits
- [ ] Reports stay read only; calculations and validation are server-side
- [ ] Tests added/updated and `bench --site <site> run-tests --app sijill` passes
- [ ] `ruff format sijill && ruff check sijill` passes
- [ ] No real company, customer, supplier or financial data in code, tests, screenshots or fixtures
- [ ] Arabic translation added in `sijill/locale/ar.po` for every new label
- [ ] CHANGELOG.md updated under [Unreleased]
- [ ] Docs site: "What's new" updated in English and Arabic, and the page of every added or changed report

<!-- Put "closes #XXXX" to auto-close the related issue. -->
