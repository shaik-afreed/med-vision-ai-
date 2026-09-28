import tensorflow as tf

TEST_PATH = "dataset/archive/chest_xray/test"
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32

test_dataset = tf.keras.utils.image_dataset_from_directory(
    TEST_PATH,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    color_mode="rgb",
    shuffle=False
)

print("Classes:", test_dataset.class_names)

model = tf.keras.models.load_model(
    "saved_models/fine_tuned_model.h5"
)

print("Fine-tuned model loaded.")

results = model.evaluate(
    test_dataset,
    verbose=1
)

print()
print("===== FINE-TUNED TEST RESULTS =====")

for name, value in zip(model.metrics_names, results):
    print(f"{name}: {value:.4f}")