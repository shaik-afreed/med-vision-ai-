import re

from pypdf import PdfReader


# ============================================================
# MEDIVISION AI - WRITTEN MEDICAL REPORT ANALYSIS
# ============================================================
#
# This extracts text from an uploaded PDF/text medical report and looks
# for lines that resemble lab-test results ("Hemoglobin  13.5 g/dL
# (12.0-16.0)"), flagging values outside a reference range. It is a
# regex-based text pattern matcher plus a lookup table of commonly
# published general adult reference ranges - NOT a trained model, NOT a
# medical NLP system, and NOT a diagnosis. It will miss values in
# unusual formats and cannot read scanned/image-only PDFs (no OCR).
# Every result this produces must be presented with that caveat - see
# build_summary() below for the exact wording used.
#
# When a report states its own reference range on the same line, that is
# always preferred over the built-in fallback table below, since real
# lab ranges vary by lab, method, age and sex in ways this table cannot
# capture.

# (aliases, unit, low, high) - general adult reference ranges, commonly
# published (e.g. Mayo Clinic / standard clinical chemistry references).
# Used only as a fallback when the report itself doesn't state a range.
KNOWN_TESTS = {
    "Hemoglobin": (["hemoglobin", "hgb", "hb"], "g/dL", 12.0, 17.5),
    "WBC Count": (
        ["wbc", "white blood cell", "white blood cell count", "leukocyte"],
        "x10^9/L", 4.0, 11.0,
    ),
    "RBC Count": (["rbc", "red blood cell", "red blood cell count"], "x10^12/L", 4.2, 5.9),
    "Platelet Count": (["platelet", "platelets", "plt"], "x10^9/L", 150, 450),
    "Fasting Glucose": (["fasting glucose", "glucose fasting", "blood glucose", "glucose"], "mg/dL", 70, 100),
    "Total Cholesterol": (["total cholesterol", "cholesterol"], "mg/dL", 0, 200),
    "LDL Cholesterol": (["ldl cholesterol", "ldl"], "mg/dL", 0, 100),
    "HDL Cholesterol": (["hdl cholesterol", "hdl"], "mg/dL", 40, 200),
    "Triglycerides": (["triglycerides"], "mg/dL", 0, 150),
    "Creatinine": (["creatinine"], "mg/dL", 0.6, 1.3),
    "ALT": (["alt", "alanine aminotransferase", "sgpt"], "U/L", 7, 56),
    "AST": (["ast", "aspartate aminotransferase", "sgot"], "U/L", 8, 48),
    "TSH": (["tsh", "thyroid stimulating hormone"], "mIU/L", 0.4, 4.0),
    "Blood Pressure Systolic": (["systolic"], "mmHg", 90, 120),
    "Blood Pressure Diastolic": (["diastolic"], "mmHg", 60, 80),
    "Sodium": (["sodium", "na+"], "mmol/L", 135, 145),
    "Potassium": (["potassium", "k+"], "mmol/L", 3.5, 5.0),
    "Total Bilirubin": (["total bilirubin", "bilirubin"], "mg/dL", 0.1, 1.2),
    "Calcium": (["calcium"], "mg/dL", 8.5, 10.5),
    "BUN": (["bun", "blood urea nitrogen", "urea"], "mg/dL", 7, 20),
}

# Sorted longest-alias-first so e.g. "fasting glucose" matches before the
# shorter, more generic "glucose".
_ALIAS_LOOKUP = sorted(
    ((alias, canonical) for canonical, (aliases, *_rest) in KNOWN_TESTS.items() for alias in aliases),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

_LINE_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9 /%().,+-]{2,45}?)\s*[:\-]?\s*"
    r"(?P<value>-?\d+\.\d+|-?\d+)\s*"
    r"(?P<unit>[a-zA-Zµ/%^0-9.]{0,15})"
)

_RANGE_PATTERN = re.compile(r"(\d+\.?\d*)\s*(?:-|–|to)\s*(\d+\.?\d*)")


def extract_text(file_path: str, content_type: str) -> str:
    """Best-effort text extraction. PDFs must contain a real text layer -
    scanned/image-only pages return no text (no OCR is performed)."""
    if content_type == "application/pdf":
        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _match_known_test(name: str):
    normalized = name.strip().lower()
    for alias, canonical in _ALIAS_LOOKUP:
        if alias in normalized:
            return canonical
    return None


def _flag_status(value: float, low: float, high: float) -> str:
    if value < low:
        return "Low"
    if value > high:
        return "High"
    return "Normal"


def parse_lab_values(text: str) -> list[dict]:
    """Scans each line of the extracted text for a recognizable
    "test name + numeric value" pattern, matches the name against the
    known-test alias table, and flags the value against either a
    reference range stated on the same line (preferred) or the built-in
    general fallback range for that test."""
    findings = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = _LINE_PATTERN.match(line)
        if not match:
            continue

        canonical = _match_known_test(match.group("name"))
        if canonical is None:
            continue

        try:
            value = float(match.group("value"))
        except ValueError:
            continue

        _aliases, default_unit, fallback_low, fallback_high = KNOWN_TESTS[canonical]
        unit = match.group("unit").strip() or default_unit

        range_match = _RANGE_PATTERN.search(line[match.end():])
        if range_match:
            low, high = float(range_match.group(1)), float(range_match.group(2))
            reference_source = "report"
        else:
            low, high = fallback_low, fallback_high
            reference_source = "general_fallback"

        findings.append({
            "test": canonical,
            "value": value,
            "unit": unit,
            "reference_range": f"{low}-{high}",
            "reference_source": reference_source,
            "status": _flag_status(value, low, high),
        })

    return findings


def build_summary(findings: list[dict], text: str) -> str:
    if not text.strip():
        return (
            "No readable text was found in this document. If it's a scanned "
            "or image-only PDF, this tool can't extract text from it (no "
            "OCR) - the original file is still saved and viewable."
        )

    if not findings:
        return (
            "The document's text was extracted, but no lab-style values in a "
            "recognized 'test name + number' format were found. This is a "
            "simple text-pattern matcher, not a medical NLP system - it may "
            "simply not recognize this report's layout. Read the extracted "
            "text directly below."
        )

    abnormal = [f for f in findings if f["status"] != "Normal"]
    from_report = sum(1 for f in findings if f["reference_source"] == "report")

    parts = [
        f"Recognized {len(findings)} lab-style value(s) in this document "
        f"({from_report} with a reference range stated in the report itself; "
        f"the rest flagged against a general adult reference range, which "
        f"may not match this patient's lab/age/sex-specific range)."
    ]

    if abnormal:
        listed = "; ".join(
            f"{f['test']} {f['value']}{f['unit']} ({f['status']}, ref {f['reference_range']})"
            for f in abnormal
        )
        parts.append(f"{len(abnormal)} value(s) fall outside the reference range: {listed}.")
    else:
        parts.append("All recognized values fall within their reference range.")

    parts.append(
        "This is an automated text-extraction and range-check tool, not a "
        "clinical interpretation or diagnosis - a qualified healthcare "
        "professional should review the original document."
    )

    return " ".join(parts)


def analyze_document(file_path: str, content_type: str) -> dict:
    text = extract_text(file_path, content_type)
    findings = parse_lab_values(text)
    summary = build_summary(findings, text)

    return {
        "raw_text": text,
        "findings": findings,
        "summary": summary,
    }
