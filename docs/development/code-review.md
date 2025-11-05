# Vertex AR Code Review Guidelines

**Version:** 1.1.0  
**Last Updated:** 2024-11-07

These guidelines describe the standards we follow when reviewing contributions to Vertex AR. They complement the process documented in [CONTRIBUTING.md](../../CONTRIBUTING.md) and the broader development practices in [docs/development/setup.md](./setup.md).

---

## 🎯 Review Goals

1. **Correctness** – The change must solve the original problem without introducing regressions.
2. **Clarity** – Code should be easy to understand and accompanied by documentation where needed.
3. **Consistency** – Follow existing patterns, naming conventions, and architecture boundaries.
4. **Security** – Never compromise on authentication, authorization, or data handling practices.
5. **Testing** – Ensure automated tests cover new behaviour and existing suites remain green.

---

## ✅ Reviewer Checklist

| Area | Questions to Ask |
|------|------------------|
| **Design** | Is the proposed solution aligned with the architecture? Does it introduce unexpected coupling? |
| **Implementation** | Are edge cases handled? Is error handling adequate? Are dependencies justified? |
| **Security & Privacy** | Are secrets protected? Are user inputs validated and sanitized? |
| **Performance** | Could the change impact NFT generation latency or API response times? |
| **Documentation** | Are README, CHANGELOG, ROADMAP, and relevant docs updated? |
| **Testing** | Do new tests cover success and failure paths? Are fixtures reusable? |

Use this checklist as a starting point and adapt based on context.

---

## 🔁 Review Workflow

1. **Triage** – Confirm the ticket scope, dependencies, and acceptance criteria.
2. **Readability First** – Skim the diff for structural changes before diving into details.
3. **Run Locally (When Needed)** – Pull the branch, execute targeted tests, and reproduce the scenario.
4. **Leave Actionable Feedback** – Be specific, constructive, and provide guidance or references.
5. **Approve or Request Changes** – Summarize the review outcome and next steps.

> Tip: When requesting changes, explain *why* and, if possible, suggest concrete improvements.

---

## 🧪 Testing Expectations

- Unit tests for pure functions and utilities
- Integration tests for API endpoints or workflows
- Regression tests when bug fixes are involved
- Update or create fixtures when adding new dependencies
- Capture coverage deltas (`pytest --cov=vertex-ar`) before merging into `main`

Refer to [docs/development/testing.md](./testing.md) for detailed testing strategy and tooling support.

---

## 🏗️ Architecture Boundaries

- **API Layer (`vertex-ar/main.py` & routers)** should not contain business logic beyond request/response handling.
- **Services & Utils** handle NFT generation, storage, and analytics.
- **Database Layer** remains encapsulated inside the repository classes.
- **Scripts** (`scripts/` directory) must avoid duplicating logic from the application modules.

When reviewing, flag any leakage across these boundaries.

---

## 🔐 Security Reviews

1. Verify authentication is enforced on privileged endpoints.
2. Confirm user-supplied data is validated (size limits, allowed types, sanitization).
3. Ensure secrets and API keys are loaded from environment variables.
4. Check for potential denial-of-service vectors (batch operations, background tasks).
5. Make sure new dependencies are from trusted sources and pinned in `requirements.txt`.

Consult [SECURITY.md](../../SECURITY.md) for the full security checklist and escalation process.

---

## 📄 Documentation Updates

Every feature or fix must include documentation updates when applicable:
- README (high-level summary and quick start)
- CHANGELOG (release notes)
- ROADMAP (status tracking)
- Implementation-specific docs (API, guides, features)

Use relative links and verify they resolve locally before merging.

---

## 🤝 Reviewer Bot & Automation

- Pre-commit hooks run formatting, linting, and security checks.
- CI pipelines execute `pytest`, linting, and type checks.
- Coverage thresholds are enforced at 60% (project-wide) with the goal of 70%.
- Deployment readiness script `check_production_readiness.sh` flags missing assets.

Reviewers should read CI failures and guide authors to the underlying fix rather than bypassing checks.

---

## 📬 Escalation & Ownership

- Security-sensitive changes require sign-off from the security champion.
- Database schema changes require consultation with the data team.
- Public API modifications must be communicated in the release notes.
- Large documentation overhauls should be split into smaller, reviewable chunks.

For urgent/blocking issues reach out via `#vertex-ar-core` in Slack or email `maintainers@vertex-ar.example.com`.

---

## 📝 Appendix: Review Comment Templates

- **Nitpick:** "Nit: consider renaming this variable to `marker_count` for clarity."
- **Suggestion:** "Suggestion: reuse the existing `validate_media()` helper instead of duplicating logic."
- **Blocking:** "Blocking: without validating `file_size` we risk uploading oversized videos."
- **Security:** "Security: please store `MINIO_SECRET_KEY` in env variables and document it in `.env.example`."
- **Docs:** "Docs: add the new endpoint to `docs/api/endpoints.md` and update the changelog."

Consistent phrasing speeds up review cycles and avoids misunderstandings.

---

Happy reviewing! Keeping these guidelines in mind helps Vertex AR stay reliable, secure, and easy to work on.
