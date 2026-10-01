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
