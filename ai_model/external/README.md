# External test: adult chest X-rays (NIH ChestX-ray14)

The deployed model (V1) and the retrained candidate B were trained only on
X-rays of children aged 1-5 from one hospital. This folder tests both on a
different population: adult X-rays from the NIH Clinical Center.

## Data

- Source: Hugging Face dataset `timm/nih-chest-xray-14` (public, no login).
- Files: the official test split, shards `data/test-00000-of-00010.parquet`
  to `data/test-00003-of-00010.parquet` (about 1.85 GB in total).
- Download each with
  `https://huggingface.co/datasets/timm/nih-chest-xray-14/resolve/main/data/<file>`.
- The parquet files are not kept: `extract` keeps only the images it needs,
  resized to 224x224, in `cache/` (git-ignored).

## Run (from `ai_model/`)

```
python external/nih_eval.py extract <path>/test-0000*.parquet
python external/nih_eval.py evaluate
```

The analysis plan is fixed in the docstring of `nih_eval.py` and was committed
before either model was run on this data. Results go to `nih_results.json`.
