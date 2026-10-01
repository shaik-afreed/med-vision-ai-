"""
Train a candidate model (same MobileNetV2 architecture as V1) on the
patient-grouped splits from prepare_data.py. V1's files are never touched:
everything is written under ai_model/improve/.

Usage:
  python improve/train_improved.py --name A --unfreeze 40 --lr2 2e-5
"""
import argparse
import json
import os
import time

import numpy as np
import tensorflow as tf

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
MODELS = os.path.join(HERE, "models")
RUNS = os.path.join(HERE, "runs")

BATCH_SIZE = 32
SEED = 42


class ArraySequence(tf.keras.utils.Sequence):
    """Shuffled mini-batches straight from the cached uint8 arrays."""

    def __init__(self, x, y, shuffle):
        super().__init__()
        self.x, self.y, self.shuffle = x, y, shuffle
        self.order = np.arange(len(x))
        self.rng = np.random.default_rng(SEED)
        if shuffle:
            self.rng.shuffle(self.order)

    def __len__(self):
        return int(np.ceil(len(self.x) / BATCH_SIZE))

    def __getitem__(self, index):
        ids = self.order[index * BATCH_SIZE:(index + 1) * BATCH_SIZE]
        return self.x[ids].astype(np.float32), self.y[ids].astype(np.float32)

    def on_epoch_end(self):
        if self.shuffle:
            self.rng.shuffle(self.order)


def build_models(dropout):
    """Returns (training_model, inference_model, base_model). Both share the
    same layer objects/weights; only the training one has augmentation. The
    inference model has the exact structure production code expects:
    raw 0-255 RGB in, preprocess_input + MobileNetV2 + GAP + Dropout + Dense."""
    augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.06),
        tf.keras.layers.RandomZoom(0.12),
        tf.keras.layers.RandomTranslation(0.06, 0.06),
        tf.keras.layers.RandomContrast(0.25),
        tf.keras.layers.RandomBrightness(0.2, value_range=(0, 255)),
    ], name="augmentation")

    base = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3), include_top=False, weights="imagenet"
    )
    base.trainable = False
    pool = tf.keras.layers.GlobalAveragePooling2D()
    drop = tf.keras.layers.Dropout(dropout)
    head = tf.keras.layers.Dense(1, activation="sigmoid")

    def head_on(x):
        return head(drop(pool(base(x, training=False))))

    train_in = tf.keras.Input(shape=(224, 224, 3))
    train_out = head_on(tf.keras.applications.mobilenet_v2.preprocess_input(augmentation(train_in)))
    training_model = tf.keras.Model(train_in, train_out, name="train_model")

    infer_in = tf.keras.Input(shape=(224, 224, 3))
    infer_out = head_on(tf.keras.applications.mobilenet_v2.preprocess_input(infer_in))
    inference_model = tf.keras.Model(infer_in, infer_out, name="inference_model")

    return training_model, inference_model, base


def compile_model(model, lr):
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")],
    )


def callbacks(patience, checkpoint_path):
    return [
        tf.keras.callbacks.ModelCheckpoint(
            checkpoint_path, monitor="val_auc", mode="max",
            save_best_only=True, save_weights_only=True, verbose=0,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_auc", mode="max", patience=patience,
            restore_best_weights=True, verbose=1,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.3, patience=2, min_lr=1e-7, verbose=1,
        ),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--unfreeze", type=int, default=40, help="last N backbone layers to fine-tune")
    parser.add_argument("--lr1", type=float, default=3e-4)
    parser.add_argument("--lr2", type=float, default=2e-5)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--epochs1", type=int, default=10)
    parser.add_argument("--epochs2", type=int, default=12)
    parser.add_argument("--resume-phase2", action="store_true",
                        help="skip phase 1 and start phase 2 from the saved phase-1 checkpoint")
    parser.add_argument("--limit", type=int, default=0, help="smoke test: use only N train images")
    args = parser.parse_args()

    os.makedirs(MODELS, exist_ok=True)
    os.makedirs(RUNS, exist_ok=True)
    tf.keras.utils.set_random_seed(SEED)

    x_train, y_train = np.load(f"{CACHE}/train_x.npy"), np.load(f"{CACHE}/train_y.npy")
    x_val, y_val = np.load(f"{CACHE}/validation_x.npy"), np.load(f"{CACHE}/validation_y.npy")
    if args.limit:
        pick = np.random.default_rng(0).permutation(len(y_train))[:args.limit]
        x_train, y_train = x_train[pick], y_train[pick]
        x_val, y_val = x_val[:args.limit // 2], y_val[:args.limit // 2]

    # Balanced class weights from the real training counts.
    n, n_pos = len(y_train), int(y_train.sum())
    class_weight = {0: n / (2 * (n - n_pos)), 1: n / (2 * n_pos)}
    print(f"[{args.name}] train {len(y_train)} (pneumonia {n_pos}), val {len(y_val)}, class_weight {class_weight}")

    training_model, inference_model, base = build_models(args.dropout)
    train_seq = ArraySequence(x_train, y_train, shuffle=True)
    val_seq = ArraySequence(x_val, y_val, shuffle=False)
    history = {"phase1": {}, "phase2": {}}
    started = time.time()

    # ---- Phase 1: frozen backbone, train the head ----
    phase1_path = os.path.join(RUNS, f"{args.name}_phase1.weights.h5")
    if args.resume_phase2:
        print(f"\n[{args.name}] PHASE 1 skipped; loading {phase1_path}")
        training_model.load_weights(phase1_path)
        h1_history = {"loss": [], "resumed_from_checkpoint": True}
    else:
        print(f"\n[{args.name}] PHASE 1 (frozen backbone, lr={args.lr1})")
        compile_model(training_model, args.lr1)
        h1 = training_model.fit(
            train_seq, validation_data=val_seq, epochs=args.epochs1,
            class_weight=class_weight, verbose=2,
            callbacks=callbacks(3, phase1_path),
        )
        h1_history = h1.history
    history["phase1"] = {k: v if not isinstance(v, list) else [float(x) for x in v] for k, v in h1_history.items()}

    # ---- Phase 2: unfreeze the last N layers (BatchNorm stays frozen) ----
    base.trainable = True
    for layer in base.layers[:-args.unfreeze]:
        layer.trainable = False
    for layer in base.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False
    trainable = sum(int(layer.trainable) for layer in base.layers)
    print(f"\n[{args.name}] PHASE 2 (fine-tune last {args.unfreeze} backbone layers, {trainable} trainable, lr={args.lr2})")

    compile_model(training_model, args.lr2)
    h2 = training_model.fit(
        train_seq, validation_data=val_seq, epochs=args.epochs2,
        class_weight=class_weight, verbose=2,
        callbacks=callbacks(4, os.path.join(RUNS, f"{args.name}_phase2.weights.h5")),
    )
    history["phase2"] = {k: [float(v) for v in vals] for k, vals in h2.history.items()}

    # ---- Save the production-shaped (no augmentation) model and verify it ----
    model_path = os.path.join(MODELS, f"{args.name}.h5")
    inference_model.save(model_path)

    reloaded = tf.keras.models.load_model(model_path)
    sample = x_val[:16].astype(np.float32)
    drift = float(np.abs(reloaded.predict(sample, verbose=0) - inference_model.predict(sample, verbose=0)).max())
    print(f"[{args.name}] saved {model_path}; reload drift {drift:.2e}")
    assert drift < 1e-5, "reloaded model does not match the trained one"

    run = {
        "name": args.name,
        "args": vars(args),
        "seed": SEED,
        "train_images": int(len(y_train)),
        "validation_images": int(len(y_val)),
        "class_weight": class_weight,
        "augmentation": "flip, rotation 0.06, zoom 0.12, translation 0.06, contrast 0.25, brightness 0.2",
        "epochs_run": {"phase1": len(h1_history["loss"]), "phase2": len(h2.history["loss"])},
        "best_val_auc_phase2": float(max(h2.history["val_auc"])),
        "train_minutes": round((time.time() - started) / 60, 1),
        "model_path": model_path,
        "history": history,
    }
    with open(os.path.join(RUNS, f"{args.name}_run.json"), "w", encoding="utf-8") as f:
        json.dump(run, f, indent=1)
    print(f"[{args.name}] DONE in {run['train_minutes']} minutes, best val AUC {run['best_val_auc_phase2']:.4f}")


if __name__ == "__main__":
    main()
