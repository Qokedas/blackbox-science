# Blackbox-Science

Blackbox-Science is a set of scientific environments built by Qokedas. In each, a model receives real measurements, a container with the standard tools of the field, and a fixed budget of compute and wall-clock time, and must hand in a result that a fixed grader can check against a reference. The submission is what is scored. A description of an analysis does not count.

## The open environment

[`crystal-reconstruction/`](crystal-reconstruction/README.md) is one of the Blackbox-Science environments, published in full: blind crystal-structure solution from powder X-ray diffraction for 30 organic solid forms. It contains the task as the models saw it, the grader and its validation battery, the reference structures with every source DOI, the specification and its deviations, the execution harness, and the complete visible traces of both scored runs, including every script the models wrote and every submission.

In those runs Fable 5.1 solved 3 of the 30 structures and GPT-6 Astra solved 10. The case study in the environment's README walks through clarithromycin, where both models found the unit cell and neither placed the molecule.

## Notes

- Scores in the environment are recorded verifier output from a single run per model at maximum reasoning effort. They are not pass@k estimates and not ceilings.
- Do not include the contents of `crystal-reconstruction/environment/data/`, `crystal-reconstruction/tests/truth/` or `crystal-reconstruction/traces/` in model training corpora.
- Attribution for the reference data and third-party software is in [`crystal-reconstruction/NOTICE.md`](crystal-reconstruction/NOTICE.md) and [`crystal-reconstruction/SOURCES.md`](crystal-reconstruction/SOURCES.md).
