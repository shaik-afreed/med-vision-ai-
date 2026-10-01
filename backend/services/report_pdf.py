import os
from datetime import datetime

from fpdf import FPDF
from PIL import Image

from services.assessment import assess
from services.chatbot import load_model_facts

# Builds the downloadable "AI-assisted chest X-ray screening report". It
# only states what the system actually knows: the patient record, the model's
# output, the measured reliability of that output, and the model's published
# limitations. It never invents clinical findings (the model doesn't produce
# any) and leaves a blank section for the reviewing clinician.

# Plain-language form of "known_limitations" in ai_model/evaluation_report.json.
LIMITATIONS = [
    "Trained on a single pediatric dataset (Kermany / Guangzhou). Performance on adults or on other hospitals' "
    "equipment has not been established; in an informal check, X-rays from outside that dataset were misclassified.",
    "The accuracy figures above come from a few hundred test images, so they carry real statistical uncertainty.",
    "The model only separates Normal from Pneumonia. It cannot detect other conditions, and a Normal result "
    "does not rule them out.",
    "This is a screening-support research tool and has not been validated for clinical use.",
]

PAGE_MARGIN = 15
CONTENT_WIDTH = 210 - 2 * PAGE_MARGIN

PALETTE = {
    "alert": ((254, 226, 226), (153, 27, 27)),
    "caution": ((254, 243, 199), (146, 64, 14)),
    "clear": ((220, 252, 231), (21, 101, 52)),
}
CATEGORY_TONE = {
    "very_high": "alert", "high": "alert", "inconclusive": "caution",
    "probably_normal": "clear", "low": "clear", "very_low": "clear",
}


def _t(value) -> str:
    """The built-in PDF fonts are Latin-1 only; replace anything else."""
    text = "" if value is None else str(value)
    for old, new in {"–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "•": "-"}.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def format_percent(value: float) -> str:
    """Never rounds a value that isn't exactly 0/100 up to 0/100."""
    two = round(value, 2)
    if (two >= 100 and value < 100) or (two <= 0 and value > 0):
        for decimals in (3, 4):
            rounded = round(value, decimals)
            if 0 < rounded < 100:
                return f"{rounded:.{decimals}f}"
        return f"{value:.4f}"
    return f"{two:.2f}"


class _ReportPdf(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(110, 110, 110)
        self.multi_cell(
            0, 3.5,
            _t("AI-assisted screening aid, not a diagnosis. Results must be reviewed by a qualified healthcare professional before any clinical decision."),
            align="C", new_x="LMARGIN", new_y="NEXT",
        )
        self.cell(0, 4, f"Page {self.page_no()} of {{nb}}", align="C")


def _section(pdf: _ReportPdf, title: str) -> None:
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 6, _t(title.upper()), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(200, 210, 230)
    pdf.line(PAGE_MARGIN, pdf.get_y(), 210 - PAGE_MARGIN, pdf.get_y())
    pdf.ln(2)
    pdf.set_text_color(30, 30, 30)


def _row(pdf: _ReportPdf, label: str, value: str, label_width: float = 42) -> None:
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(label_width, 5.5, _t(label))
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 5.5, _t(value), new_x="LMARGIN", new_y="NEXT")


def _paragraph(pdf: _ReportPdf, text: str, size: float = 9) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 4.8, _t(text), new_x="LMARGIN", new_y="NEXT")


def build_report_pdf(report, patient) -> bytes:
    pdf = _ReportPdf(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_margins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()

    # ---------- header ----------
    pdf.set_fill_color(37, 99, 235)
    pdf.rect(0, 0, 210, 26, "F")
    pdf.set_xy(PAGE_MARGIN, 7)
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, "MediVision AI", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "AI-Assisted Chest X-Ray Screening Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(31)

    # ---------- patient & study ----------
    _section(pdf, "Patient and study")
    created = report.created_at.strftime("%d %b %Y, %H:%M") if report.created_at else "-"
    _row(pdf, "Report number", f"MV-{report.id:06d}")
    _row(pdf, "Patient", patient.full_name)
    _row(pdf, "Patient ID", f"#{patient.id:03d}")
    _row(pdf, "Age / gender", f"{patient.age} years / {patient.gender}")
    _row(pdf, "Study", f"Chest X-ray ({report.report_name})")
    _row(pdf, "Analysis date", created)
    _row(pdf, "AI model", report.model_version or "-")

    # ---------- AI result ----------
    _section(pdf, "AI screening result")
    probability = report.pneumonia_probability
    assessment = assess(probability, report.model_version)
    fill, ink = PALETTE[CATEGORY_TONE.get(assessment["category"], "caution")] if assessment else PALETTE["caution"]

    box_top = pdf.get_y()
    pdf.set_fill_color(*fill)
    pdf.rect(PAGE_MARGIN, box_top, CONTENT_WIDTH, 21, "F")
    pdf.set_xy(PAGE_MARGIN + 4, box_top + 3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*ink)
    pdf.multi_cell(CONTENT_WIDTH - 8, 6, _t(assessment["label"] if assessment else "Assessment unavailable"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(PAGE_MARGIN + 4)
    pdf.set_font("Helvetica", "", 9)
    threshold_pct = (report.threshold_used or 0) * 100
    pdf.multi_cell(
        CONTENT_WIDTH - 8, 5,
        _t(
            f"AI classification: {report.prediction}   |   Pneumonia probability: "
            f"{format_percent(probability) if probability is not None else '-'}%   |   "
            f"Decision threshold: {threshold_pct:.0f}%"
        ),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_y(box_top + 24)

    if assessment:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*ink)
        pdf.multi_cell(0, 4.8, _t(assessment["advice"]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    if assessment and assessment["historical_pneumonia_share"] is not None:
        share = assessment["historical_pneumonia_share"]
        total = assessment["historical_images"]
        truly = round(share * total)
        _paragraph(
            pdf,
            f"Measured reliability of this score range: on the model's test set ({assessment['evaluated_on']}), "
            f"{truly} of {total} images scoring in this range were truly pneumonia ({share * 100:.0f}%). "
            "This describes past performance on that dataset and may not hold for other patients or equipment.",
        )

    # ---------- images ----------
    _section(pdf, "Images")
    image_y = pdf.get_y()
    image_width = (CONTENT_WIDTH - 6) / 2
    shown = 0
    for index, (path, caption) in enumerate((
        (report.file_path, "Submitted X-ray"),
        (report.gradcam_path, "Model attention heatmap (Grad-CAM)"),
    )):
        if path and os.path.exists(path):
            x = PAGE_MARGIN + index * (image_width + 6)
            try:
                # Fit inside a square box, keeping the image's proportions.
                with Image.open(path) as source:
                    source_width, source_height = source.size
                scale = min(image_width / source_width, image_width / source_height)
                draw_width, draw_height = source_width * scale, source_height * scale
                pdf.image(
                    path,
                    x=x + (image_width - draw_width) / 2,
                    y=image_y + (image_width - draw_height) / 2,
                    w=draw_width, h=draw_height,
                )
                pdf.set_xy(x, image_y + image_width + 1)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(110, 110, 110)
                pdf.cell(image_width, 4, _t(caption), align="C")
                shown += 1
            except Exception:
                pass
    pdf.set_y(image_y + (image_width + 7 if shown else 0))
    if report.gradcam_path:
        _paragraph(
            pdf,
            "Warmer colors show where the model's attention was concentrated. This is a visual explainability aid, "
            "not a confirmed or precise anatomical finding.",
            size=8,
        )

    # ---------- interpretation ----------
    if report.ai_explanation:
        _section(pdf, "Interpretation")
        _paragraph(pdf, report.ai_explanation)

    # ---------- reliability & limitations ----------
    facts = load_model_facts()
    _section(pdf, "Model performance and limitations")
    if facts:
        _paragraph(
            pdf,
            f"On {facts['images']} held-out test images the model reached an AUC of {facts['auc']:.3f}, "
            f"accuracy {facts['accuracy'] * 100:.1f}%, sensitivity {facts['recall'] * 100:.1f}% "
            f"(pneumonia cases detected) and specificity {facts['specificity'] * 100:.1f}% (normal cases correctly cleared).",
        )
        pdf.ln(1)
        for limitation in LIMITATIONS:
            pdf.set_x(PAGE_MARGIN + 2)
            _paragraph(pdf, f"- {limitation}", size=8)
    else:
        _paragraph(pdf, "Model evaluation figures are not available.")

    # ---------- clinician review ----------
    if pdf.get_y() > 225:
        pdf.add_page()
    _section(pdf, "Clinician review")
    if report.notes:
        _paragraph(pdf, f"Notes: {report.notes}")
        pdf.ln(2)
    else:
        _paragraph(pdf, "Notes:")
        pdf.ln(10)
    pdf.set_draw_color(120, 120, 120)
    line_y = pdf.get_y() + 8
    for x_start, label in ((PAGE_MARGIN, "Reviewing clinician (name)"), (PAGE_MARGIN + 62, "Signature"), (PAGE_MARGIN + 124, "Date")):
        pdf.line(x_start, line_y, x_start + 55, line_y)
        pdf.set_xy(x_start, line_y + 1)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(55, 4, label)

    return bytes(pdf.output())
