import pytest

from services.assessment import assess

V1 = "mobilenetv2-finetuned-v1"


@pytest.mark.parametrize(
    "probability, category",
    [
        (99.2, "very_high"), (95.0, "very_high"), (100.0, "very_high"),
        (94.99, "high"), (82.0, "high"),
        (81.99, "inconclusive"), (70.28, "inconclusive"), (67.0, "inconclusive"),
        (66.99, "probably_normal"), (50.0, "probably_normal"),
        (49.9, "low"), (20.0, "low"),
        (19.9, "very_low"), (0.0, "very_low"),
    ],
)
def test_assessment_bands_match_the_measured_table(probability, category):
    assert assess(probability, V1)["category"] == category


def test_borderline_band_reports_its_measured_reliability():
    result = assess(76.77, V1)
    assert result["historical_images"] == 36
    assert 0.5 < result["historical_pneumonia_share"] < 0.56
    assert "not" in result["advice"].lower() and "reassuring" in result["advice"].lower()


def test_historical_figures_are_withheld_for_a_different_model_version():
    result = assess(76.77, "some-other-model")
    assert result["category"] == "inconclusive"
    assert result["historical_pneumonia_share"] is None
    assert result["historical_images"] is None


def test_no_probability_gives_no_assessment():
    assert assess(None, V1) is None


@pytest.mark.parametrize("age", [11, 30, 45, 80])
def test_patients_older_than_the_training_ages_get_no_likelihood_label(age):
    result = assess(99.35, V1, patient_age=age)
    assert result["category"] == "outside_training_ages"
    assert "trained only on X-rays of young children" in result["label"]
    assert result["historical_pneumonia_share"] is None
    assert result["score_category"] == "very_high"


@pytest.mark.parametrize("age", [0, 1, 5, 10])
def test_children_within_the_training_ages_keep_the_measured_bands(age):
    result = assess(99.35, V1, patient_age=age)
    assert result["category"] == "very_high"
    assert result["score_category"] == "very_high"
    assert result["historical_images"] is not None


def test_unknown_age_keeps_the_measured_bands():
    assert assess(99.35, V1)["category"] == "very_high"


def test_image_flagged_as_unlike_training_data_is_unreliable_even_for_a_child():
    result = assess(99.35, V1, patient_age=4, domain_score=0.97)
    assert result["category"] == "unlike_training_images"
    assert "does not look like the children's X-rays" in result["label"]
    assert result["historical_pneumonia_share"] is None
    assert result["score_category"] == "very_high"


def test_image_that_looks_like_training_data_keeps_the_measured_bands():
    assert assess(99.35, V1, patient_age=4, domain_score=0.02)["category"] == "very_high"
    assert assess(99.35, V1, patient_age=4, domain_score=None)["category"] == "very_high"


def test_age_rule_still_takes_precedence_over_the_image_check():
    assert assess(99.35, V1, patient_age=40, domain_score=0.97)["category"] == "outside_training_ages"
