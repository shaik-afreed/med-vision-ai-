import os

import numpy as np
from PIL import Image

from services.prediction import get_model, IMAGE_SIZE


# ============================================================
# MEDIVISION AI - GRAD-CAM EXPLAINABILITY
# ============================================================
#
# This produces a Grad-CAM attention heatmap: which pixels of the input
# X-ray most influenced the model's sigmoid output. It is a visualization
# of what the model attended to, not a validated clinical finding and not
# a precise anatomical localization (no lung-side/lobe metadata is used).
# Every caller-facing string produced here says so explicitly - see
# ai_model/v2/... audit notes in project history for why overclaiming
# explainability tools is treated as seriously as overclaiming accuracy.
#
# Reuses the same already-loaded V1 model from services.prediction (no
# second copy loaded into memory, and no chance of drifting from the
# model actually used for the prediction being explained).

_base_model = None
_post_base_layers = None
_conv_submodel = None


def _build_gradcam_components():
    """Lazily splits the loaded model into (a) the MobileNetV2 backbone's
    own input -> last-feature-map graph, used as-is since it's the backbone's
    own construction context, and (b) the list of layers that come after the
    backbone in the outer model (GlobalAveragePooling2D, Dropout, Dense),
    replayed manually inside the GradientTape. This two-piece approach is
    required because a nested Keras submodel's `.output` tensors don't
    connect to the outer model's graph the way a plain functional layer's
    would - see project notes for why a naive `Model(model.inputs,
    [base_model.get_layer(...).output, model.output])` doesn't work here.
    """
    global _base_model, _post_base_layers, _conv_submodel

    if _conv_submodel is not None:
        return

    import tensorflow as tf

    model = get_model()

    base_model = None
    post_layers = []

    for layer in model.layers:
        # The data_augmentation block is also a tf.keras.Model (Sequential
        # is a Model subclass) and appears earlier in the graph than the
        # MobileNetV2 backbone - it must be excluded explicitly, or it gets
        # mistaken for the backbone and everything downstream (the real
        # backbone, GAP, Dropout, Dense) ends up misclassified as "layers
        # after the backbone" and fails when replayed manually.
        is_backbone_candidate = isinstance(layer, tf.keras.Model) and not isinstance(
            layer, tf.keras.Sequential
        )
        if base_model is None and is_backbone_candidate:
            base_model = layer
            continue
        if base_model is not None:
            post_layers.append(layer)

    if base_model is None:
        raise RuntimeError(
            "Grad-CAM setup failed: no nested backbone model found inside "
            "the loaded prediction model."
        )

    _base_model = base_model
    _post_base_layers = post_layers
    _conv_submodel = tf.keras.Model(base_model.input, base_model.layers[-1].output)


def _forward_from_conv(conv_output):
    x = conv_output
    for layer in _post_base_layers:
        x = layer(x, training=False)
    return x


def _compute_heatmap(image_array):
    """image_array: float32 numpy array, shape (1, H, W, 3), raw 0-255
    pixel values - same format predict_disease() feeds the model."""
    import tensorflow as tf

    _build_gradcam_components()

    preprocessed = tf.keras.applications.mobilenet_v2.preprocess_input(
        tf.convert_to_tensor(image_array)
    )

    with tf.GradientTape() as tape:
        conv_output = _conv_submodel(preprocessed, training=False)
        tape.watch(conv_output)
        prediction = _forward_from_conv(conv_output)
        target = prediction[:, 0]

    grads = tape.gradient(target, conv_output)

    if grads is None:
        raise RuntimeError("Grad-CAM gradient computation returned no gradient.")

    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_output = conv_output[0]
    heatmap = conv_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0)

    max_value = tf.reduce_max(heatmap)
    if max_value > 0:
        heatmap = heatmap / max_value

    return heatmap.numpy()


def _colorize_heatmap(heatmap, size):
    """0..1 heatmap -> an RGBA 'hot' overlay (black/red/yellow/white),
    implemented with plain numpy so no matplotlib/opencv dependency is
    needed just for a colormap."""
    heat_img = Image.fromarray(np.uint8(heatmap * 255)).resize(
        size, resample=Image.BILINEAR
    )
    heat = np.asarray(heat_img).astype(np.float32) / 255.0

    r = np.clip(heat * 3.0, 0, 1)
    g = np.clip(heat * 3.0 - 1.0, 0, 1)
    b = np.clip(heat * 3.0 - 2.0, 0, 1)
    alpha = heat * 180  # semi-transparent, so the underlying X-ray stays visible

    rgba = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    rgba[..., 0] = (r * 255).astype(np.uint8)
    rgba[..., 1] = (g * 255).astype(np.uint8)
    rgba[..., 2] = (b * 255).astype(np.uint8)
    rgba[..., 3] = alpha.astype(np.uint8)

    return Image.fromarray(rgba)


def _describe_focus_region(heatmap):
    h, w = heatmap.shape
    mid_h, mid_w = h // 2, w // 2

    quadrants = {
        "upper-left": heatmap[:mid_h, :mid_w].mean(),
        "upper-right": heatmap[:mid_h, mid_w:].mean(),
        "lower-left": heatmap[mid_h:, :mid_w].mean(),
        "lower-right": heatmap[mid_h:, mid_w:].mean(),
    }

    return max(quadrants, key=quadrants.get)


def generate_gradcam(file_path, disease, pneumonia_probability, threshold, output_path):
    """
    Generates a Grad-CAM heatmap overlay for the X-ray at file_path and
    saves it as a PNG at output_path. Returns a short, honest,
    template-generated (not LLM-generated, not fabricated) explanation
    string describing the result and where the model's attention
    concentrated.

    disease: "Pneumonia" or "Normal" (from predict_disease's result).
    pneumonia_probability: 0-100 float (predict_disease's
        "pneumonia_probability").
    threshold: 0-1 float (predict_disease's "threshold").
    """
    image = Image.open(file_path).convert("RGB").resize(IMAGE_SIZE)
    image_array = np.expand_dims(np.array(image).astype(np.float32), axis=0)

    heatmap = _compute_heatmap(image_array)

    overlay = _colorize_heatmap(heatmap, IMAGE_SIZE)
    combined = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined.save(output_path, format="PNG")

    region = _describe_focus_region(heatmap)
    threshold_pct = threshold * 100

    if disease == "Pneumonia":
        explanation = (
            f"The AI classified this X-ray as Pneumonia, with a "
            f"{pneumonia_probability:.2f}% pneumonia probability - above the "
            f"{threshold_pct:.0f}% decision threshold. The heatmap below shows "
            f"where the model's attention concentrated most (the {region} "
            f"region of the image), which is the area that most influenced "
            f"this result. This heatmap is a visual attention map, not a "
            f"confirmed diagnosis or a precise anatomical location - a "
            f"qualified radiologist should review the original image directly."
        )
    else:
        explanation = (
            f"The AI classified this X-ray as Normal: the pneumonia "
            f"probability ({pneumonia_probability:.2f}%) stayed below the "
            f"{threshold_pct:.0f}% decision threshold. The heatmap below shows "
            f"where the model's attention was concentrated ({region} region of "
            f"the image); for a Normal result this does not indicate any "
            f"specific finding. This is an AI-assisted screening aid, not a "
            f"confirmed diagnosis - a qualified radiologist should review the "
            f"original image directly."
        )

    return explanation
