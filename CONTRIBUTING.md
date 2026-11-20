# Contributing

Thank you for helping build a credible motorsport research tool.

1. Create an issue describing a specific research or engineering problem.
2. Include the data source and its permission terms, expected behaviour, baseline and acceptance tests.
3. Implement changes on a feature branch, not directly on `main`.
4. Run `ruff check src tests` and `pytest -q`.
5. For numerical changes, include fixed-seed tests and out-of-sample evaluation. Describe limitations.
6. Never commit secrets, private team data, model weights of uncertain origin, or data that is not licensed to redistribute.

This project prioritizes reproducible evidence, transparency and clearly differentiated synthetic vs real data.
