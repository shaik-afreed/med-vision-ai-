import os
import tensorflow as tf

# ==============================
# SETTINGS
# ==============================

DATASET_PATH = "dataset/archive/chest_xray/train"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
SEED = 42

INITIAL_MODEL = "saved_models/best_model.h5"
FINE_TUNED_MODEL = "saved_models/fine_tuned_model.h5"


# ==============================
# LOAD DATA
# ==============================

train_dataset = tf.keras.utils.image_dataset_from_directory(
    DATASET_PATH,
    validation_split=0.20,
    subset="training",
    seed=SEED,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    color_mode="rgb"
)

validation_dataset = tf.keras.utils.image_dataset_from_directory(
    DATASET_PATH,
    validation_split=0.20,
    subset="validation",
    seed=SEED,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    color_mode="rgb",
    shuffle=False
)

print()
print("Classes:", train_dataset.class_names)


# ==============================
# LOAD PHASE 1 MODEL
# ==============================

model = tf.keras.models.load_model(
    INITIAL_MODEL
)

print()
print("Phase 1 model loaded successfully.")


# ==============================
# FIND MOBILENETV2 BASE MODEL
# ==============================

base_model = None

for layer in model.layers:

    if isinstance(
        layer,
        tf.keras.Model
    ):
        if "mobilenetv2" in layer.name.lower():
            base_model = layer
            break


if base_model is None:

    raise ValueError(
        "MobileNetV2 base model not found."
    )


print()
print("Base model:", base_model.name)


# ==============================
# UNFREEZE TOP LAYERS
# ==============================

base_model.trainable = True

# Freeze most layers
for layer in base_model.layers[:-30]:

    layer.trainable = False

# Keep BatchNormalization layers frozen
for layer in base_model.layers:

    if isinstance(
        layer,
        tf.keras.layers.BatchNormalization
    ):
        layer.trainable = False


# ==============================
# COMPILE FOR FINE-TUNING
# ==============================

model.compile(

    optimizer=tf.keras.optimizers.Adam(
        learning_rate=1e-5
    ),

    loss="binary_crossentropy",

    metrics=[
        "accuracy",
        tf.keras.metrics.Precision(
            name="precision"
        ),
        tf.keras.metrics.Recall(
            name="recall"
        ),
        tf.keras.metrics.AUC(
            name="auc"
        )
    ]
)


# ==============================
# CLASS WEIGHTS
# ==============================

normal_count = 1341
pneumonia_count = 3875

total = normal_count + pneumonia_count

class_weights = {

    0: total / (2 * normal_count),

    1: total / (2 * pneumonia_count)
}


# ==============================
# CALLBACKS
# ==============================

os.makedirs(
    "saved_models",
    exist_ok=True
)

checkpoint = tf.keras.callbacks.ModelCheckpoint(

    FINE_TUNED_MODEL,

    monitor="val_auc",

    mode="max",

    save_best_only=True,

    verbose=1
)

early_stopping = tf.keras.callbacks.EarlyStopping(

    monitor="val_auc",

    mode="max",

    patience=3,

    restore_best_weights=True,

    verbose=1
)

reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(

    monitor="val_loss",

    factor=0.2,

    patience=1,

    min_lr=1e-7,

    verbose=1
)


# ==============================
# FINE-TUNING
# ==============================

print()
print("========================================")
print("      STARTING PHASE 2 FINE-TUNING")
print("========================================")

history = model.fit(

    train_dataset,

    validation_data=validation_dataset,

    epochs=10,

    class_weight=class_weights,

    callbacks=[
        checkpoint,
        early_stopping,
        reduce_lr
    ]
)


print()
print("========================================")
print("      FINE-TUNING COMPLETED")
print("========================================")
