# Contributing to RuralRoute

Public transport gaps affect real people, so correctness and clear limitations
matter more than flashy claims.

1. Before proposing an extension, open an issue describing the actual transport
   problem and a minimal public or fictional example.
2. Fork, branch, and add a **regression test** alongside the code change.
3. Run `python -m pytest -q` and `ruff check src tests`.
4. Submit a pull request explaining how behaviour differs and what is unsupported.
5. Maintainers review correctness, privacy, licensing, and compatibility before merging.

Do not upload access tokens, personally identifying rider logs, private feeds or
copyrighted timetable material without permission. Use synthetic CSV fixtures.

This project does not claim community traction or safety certification. We welcome
practical critique and real examples from passenger groups, operators and councils.
