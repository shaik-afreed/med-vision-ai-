import os
import tensorflow as tf

# ==============================
# SETTINGS
# ==============================

DATASET_PATH = "dataset/archive/chest_xray/train"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
SEED = 42


# ==============================
# LOAD TRAINING DATA
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


# ==============================
# LOAD VALIDATION DATA
# ==============================

validation_dataset = tf.keras.utils.image_dataset_from_directory(
    DATASET_PATH,
    validation_split=0.20,
    subset="validation",
    seed=SEED,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    color_mode="rgb"
)


# ==============================
# CLASS NAMES
# ==============================

class_names = train_dataset.class_names

print()
print("Classes:", class_names)


# ==============================
# DATA AUGMENTATION
# ==============================

data_augmentation = tf.keras.Sequential([
    tf.keras.layers.RandomFlip("horizontal"),
    tf.keras.layers.RandomRotation(0.05),
    tf.keras.layers.RandomZoom(0.10),
])


# ==============================
# LOAD MOBILENETV2
# ==============================

base_model = tf.keras.applications.MobileNetV2(
    input_shape=(224, 224, 3),
    include_top=False,
    weights="imagenet"
)


# Freeze the pretrained layers
base_model.trainable = False


# ==============================
# BUILD MODEL
# ==============================

inputs = tf.keras.Input(
    shape=(224, 224, 3)
)

x = data_augmentation(inputs)

x = tf.keras.applications.mobilenet_v2.preprocess_input(x)

x = base_model(
    x,
    training=False
)

x = tf.keras.layers.GlobalAveragePooling2D()(x)

x = tf.keras.layers.Dropout(0.3)(x)

outputs = tf.keras.layers.Dense(
    1,
    activation="sigmoid"
)(x)

model = tf.keras.Model(
    inputs,
    outputs
)


# ==============================
# COMPILE MODEL
# ==============================

model.compile(
    optimizer=tf.keras.optimizers.Adam(
        learning_rate=0.0001
    ),
    loss="binary_crossentropy",
    metrics=[
        "accuracy",
        tf.keras.metrics.Precision(name="precision"),
        tf.keras.metrics.Recall(name="recall"),
        tf.keras.metrics.AUC(name="auc")
    ]
)


# ==============================
# MODEL SUMMARY
# ==============================

print()
print("===== MODEL SUMMARY =====")

model.summary()

# ==============================
# CLASS WEIGHTS
# ==============================

normal_count = 1341
pneumonia_count = 3875

total = normal_count + pneumonia_count

weight_normal = total / (2 * normal_count)
weight_pneumonia = total / (2 * pneumonia_count)

class_weights = {
    0: weight_normal,
    1: weight_pneumonia
}

print()
print("===== CLASS WEIGHTS =====")
print("NORMAL:", weight_normal)
print("PNEUMONIA:", weight_pneumonia)


# ==============================
# CALLBACKS
# ==============================

os.makedirs("saved_models", exist_ok=True)

checkpoint = tf.keras.callbacks.ModelCheckpoint(
    "saved_models/best_model.h5",
    monitor="val_auc",
    mode="max",
    save_best_only=True,
    verbose=1
)

early_stopping = tf.keras.callbacks.EarlyStopping(
    monitor="val_auc",
    mode="max",
    patience=5,
    restore_best_weights=True,
    verbose=1
)

reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
    monitor="val_loss",
    factor=0.2,
    patience=2,
    min_lr=1e-7,
    verbose=1
)

# ==============================
# PHASE 1 TRAINING
# ==============================

print()
print("===== STARTING PHASE 1 TRAINING =====")

history = model.fit(
    train_dataset,
    validation_data=validation_dataset,
    epochs=15,
    class_weight=class_weights,
    callbacks=[
        checkpoint,
        early_stopping,
        reduce_lr
    ]
)

print()
print("===== TRAINING COMPLETED =====")
