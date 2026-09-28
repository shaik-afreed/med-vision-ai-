# Archived evaluation scripts

These scripts were superseded by [`ai_model/evaluate_model.py`](../evaluate_model.py),
the single authoritative evaluation pipeline. They're kept for reference/history,
not for producing reported metrics.

Reasons they were retired:

- `evaluate.py`, `evaluate_finetuned.py`, `confusion_matrix.py`,
  `confusion_matrix_finetuned.py`, `compare_models.py` — used the default
  `0.5` threshold with no justification, and read images via TF's
  `image_dataset_from_directory` pipeline rather than the PIL path
  production actually uses.
- `final_test.py` (threshold `0.40`), `final_test_correct.py` (threshold
  `0.50`) — different hardcoded thresholds, neither derived from a
  validation split.
- `threshold_analysis.py` — correctly swept thresholds against a
  validation split, but used an independently reconstructed split that
  wasn't provably identical to the one used during training.
- `threshold_test_analysis.py` and `FINAL_THRESHOLD_ANALYSIS.py` — swept
  thresholds **directly against the test set** and picked the
  best-looking one. This is test-set leakage: it invalidates any
  "unbiased" performance claim made using that same test set afterward.
  The `0.66` threshold previously hardcoded in
  `backend/services/prediction.py` most likely traces back to this kind
  of exploratory, test-set-tuned analysis.

`ai_model/evaluate_model.py` fixes all of the above: it reconstructs the
*exact* validation split training used (same seed, same
`image_dataset_from_directory` call, read via `.file_paths`), selects the
threshold via Youden's J on validation only, and evaluates the test set
exactly once at that fixed threshold.
