# ruff: noqa: E702
"""Makes made-up patient documents to try the Upload page with (PDF, Word, CSV, Excel, plus one image the system should refuse).

    python scripts/make_sample_documents.py            # writes sample_documents/

The people and numbers are invented. Nothing here is real patient data.
"""
import csv
import random
import sys
from pathlib import Path

from docx import Document
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parents[1] / "sample_documents"
S = getSampleStyleSheet()
NOTE = "Made-up sample for testing PranaSync. Not a real patient."


def pdf(name, title, header, rows=None, lines=None, cols=("Test", "Result", "Unit", "Reference")):
    doc = SimpleDocTemplate(str(OUT / name), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm, title=title)
    flow = [Paragraph(title, S["Title"])] + [Paragraph(x, S["Normal"]) for x in header] + [Spacer(1, 8)]
    if rows:
        t = Table([list(cols)] + rows, colWidths=[62 * mm, 28 * mm, 26 * mm, 50 * mm], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6d2fa6")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .4, colors.grey),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f0f8")]), ("FONTSIZE", (0, 0), (-1, -1), 10)]))
        flow.append(t)
    for ln in lines or []:
        flow += [Spacer(1, 4), Paragraph(ln, S["Normal"])]
    flow += [Spacer(1, 14), Paragraph(NOTE, S["Italic"])]
    doc.build(flow)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    # ---- Person A: Ravi Kumar, 58, raised blood sugar, cholesterol and blood pressure. Three documents, to watch the picture grow.
    pdf("A1_Ravi_lab_report_blood_sugar_and_cholesterol.pdf", "City Lab: Blood Sugar and Cholesterol Report",
        ["Patient: Ravi Kumar    Sex: Male    Age: 58 years", "Date of birth: 1968-02-11", "Report date: 12 September 2026"],
        [["Fasting glucose", "148", "mg/dL", "70 - 99"], ["HbA1c", "7.1", "%", "4.0 - 5.6"], ["Total cholesterol", "245", "mg/dL", "< 200"], ["LDL cholesterol", "162", "mg/dL", "< 100"],
         ["HDL cholesterol", "36", "mg/dL", "> 40"], ["Triglycerides", "240", "mg/dL", "< 150"]])
    pdf("A2_Ravi_clinic_visit_note.pdf", "Riverside Family Clinic: Visit Note",
        ["Patient: Ravi Kumar    Sex: Male    Age: 58", "Visit date: 20 September 2026"], None,
        ["Blood pressure: 152/94 mmHg (seated, right arm).", "Resting heart rate: 82 bpm.", "Height 172 cm   Weight 96 kg.", "Smoking: former smoker.", "Alcohol: 6 drinks/week.",
         "Exercise: 1 session per week.", "Family history: father had a heart attack at 55; mother has diabetes.", "Plan: review in 3 months. Lifestyle advice given."])
    rng = random.Random(8)
    with (OUT / "A3_Ravi_fitness_tracker_export.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["Date", "Steps", "Active minutes", "Sleep hours", "Resting heart rate"])
        for d in range(1, 31):
            w.writerow([f"2026-09-{d:02d}", rng.randint(2600, 4800), rng.randint(8, 24), round(rng.uniform(5.2, 6.6), 1), rng.randint(79, 86)])
    pdf("A4_Ravi_followup_lab_report_2_months_later.pdf", "City Lab: Blood Sugar and Cholesterol Report (follow-up)",
        ["Patient: Ravi Kumar    Sex: Male    Age: 58 years", "Report date: 12 November 2026"],
        [["Fasting glucose", "132", "mg/dL", "70 - 99"], ["HbA1c", "6.7", "%", "4.0 - 5.6"], ["Total cholesterol", "221", "mg/dL", "< 200"], ["LDL cholesterol", "141", "mg/dL", "< 100"],
         ["HDL cholesterol", "40", "mg/dL", "> 40"], ["Triglycerides", "198", "mg/dL", "< 150"]],
        ["Blood pressure: 144/90 mmHg.", "Height 172 cm   Weight 91 kg."])
    # ---- Person B: Meera Iyer, 34, healthy. One combined report.
    pdf("B1_Meera_healthy_checkup_report.pdf", "Wellness Centre: Annual Health Check",
        ["Patient: Meera Iyer    Sex: Female    Age: 34 years", "Report date: 03 October 2026"],
        [["Fasting glucose", "86", "mg/dL", "70 - 99"], ["HbA1c", "5.1", "%", "4.0 - 5.6"], ["Total cholesterol", "172", "mg/dL", "< 200"], ["LDL cholesterol", "88", "mg/dL", "< 100"],
         ["HDL cholesterol", "64", "mg/dL", "> 50"], ["Triglycerides", "92", "mg/dL", "< 150"]],
        ["Blood pressure: 112/70 mmHg.", "Resting heart rate: 62 bpm.", "Height 165 cm   Weight 58 kg.", "Smoking: never smoked.", "Alcohol: 1 drinks/week.", "Exercise: 4 sessions per week.", "Average daily steps: 9400."])
    # ---- Person C: one document with only blood sugar, to show a single document is enough for one area and says what else is needed.
    d = Document(); d.add_heading("Pharmacy Screening Result", 1)
    d.add_paragraph("Patient: Sam Okafor    Sex: Male    Age: 52 years"); d.add_paragraph("Date: 5 November 2026")
    t = d.add_table(rows=1, cols=3); t.style = "Light Grid Accent 1"
    for c, x in zip(t.rows[0].cells, ("Test", "Result", "Unit")):
        c.text = x
    for a, b, c in (("Fasting glucose", "112", "mg/dL"), ("HbA1c", "6.1", "%")):
        r = t.add_row().cells; r[0].text, r[1].text, r[2].text = a, b, c
    d.add_paragraph(NOTE); d.save(str(OUT / "C1_Sam_blood_sugar_only.docx"))
    # ---- Person D: units in mmol/L and mmol/mol (UK / Canada style), to show unit conversion.
    pdf("D1_Priya_lab_report_mmol_units.pdf", "Hospital Laboratory: Results (SI units)",
        ["Patient: Priya Nair    Sex: Female    Age: 47 years", "Report date: 18 October 2026"],
        [["Fasting glucose", "6.4", "mmol/L", "3.9 - 5.5"], ["HbA1c", "46", "mmol/mol", "20 - 38"], ["Total cholesterol", "5.9", "mmol/L", "< 5.2"], ["LDL cholesterol", "3.8", "mmol/L", "< 2.6"],
         ["HDL cholesterol", "1.1", "mmol/L", "> 1.3"], ["Triglycerides", "2.2", "mmol/L", "< 1.7"]], ["Blood pressure: 136/86 mmHg.", "Height 160 cm   Weight 78 kg."])
    # ---- Person E: results as an Excel sheet.
    wb = Workbook(); ws = wb.active; ws.title = "Results"
    ws.append(["Patient", "Arun Das"]); ws.append(["Age", 63]); ws.append(["Sex", "Male"]); ws.append([])
    ws.append(["Test", "Result", "Unit"])
    for r in (("Fasting glucose", 131, "mg/dL"), ("HbA1c", 6.8, "%"), ("LDL cholesterol", 171, "mg/dL"), ("HDL cholesterol", 39, "mg/dL"), ("Total cholesterol", 252, "mg/dL"),
              ("Triglycerides", 210, "mg/dL"), ("Systolic blood pressure", 158, "mmHg"), ("Diastolic blood pressure", 98, "mmHg")):
        ws.append(list(r))
    wb.save(str(OUT / "E1_Arun_lab_results.xlsx"))
    # ---- G: three documents for the review page, the clinical view and the optional AI second reader
    pdf("G1_Full_workup_Kofi_all_values.pdf", "Riverside Clinic: Complete Health Work-up",
        ["Patient: Kofi Mensah    Sex: Male    Age: 61 years", "Visit date: 9 November 2026"],
        [["Fasting glucose", "139", "mg/dL", "70 - 99"], ["HbA1c", "7.3", "%", "4.0 - 5.6"], ["Total cholesterol", "238", "mg/dL", "< 200"], ["LDL cholesterol", "158", "mg/dL", "< 100"],
         ["HDL cholesterol", "38", "mg/dL", "> 40"], ["Triglycerides", "210", "mg/dL", "< 150"]],
        ["Blood pressure: 148/92 mmHg.", "Resting heart rate: 78 bpm.", "Height 174 cm   Weight 94 kg.", "Smoking: former smoker.", "Alcohol: 5 drinks/week.", "Exercise: 1 session per week.",
         "Average daily steps: 3800.", "Sleep: 5.5 hours per night.", "Family history: father had a heart attack at 54; mother has diabetes."])
    pdf("G2_Unusual_wording_note_AI_second_reader.pdf", "Riverside Clinic: Follow-up Note",
        ["Mr. Kofi Mensah, 61 years, male.", "Seen on 9 November 2026."], None,
        ["At the visit his blood pressure was 148/92 and his resting pulse 78 beats a minute.", "The three-month sugar marker was 7.3% this time. Plasma glucose, fasted for 10 hours ........ 139 mg/dL",
         "TC 238 mg/dL, LDL-C 158, HDL-C 36, Trigs 210.", "He weighs 94 kg and stands 174 cm tall.", "He sleeps about 5.5 hours a night and walks roughly 3800 steps a day.",
         "Former smoker. Drinks about 5 drinks a week. His father had a heart attack at 54."])
    pdf("G3_Range_printed_before_result_review_practice.pdf", "City Lab: Results (range shown first)",
        ["Patient: Dana Whitfield    Sex: Female    Age: 54 years", "Report date: 12 October 2026"], None,
        ["Fasting glucose (70-99 mg/dL)    131 mg/dL", "HbA1c (4.0-5.6 %)    6.6 %", "LDL cholesterol (< 100 mg/dL)    171 mg/dL", "HDL cholesterol (> 50 mg/dL)    41 mg/dL",
         "Triglycerides (target < 150)    205 mg/dL", "Blood pressure: 138/86 mmHg.", "Height 163 cm   Weight 79 kg."])
    # ---- a photo and a scan of a report: read on this computer by OCR, every value marked for checking
    try:
        from PIL import Image, ImageDraw, ImageFont
        lines = ["City Lab - Blood Sugar and Cholesterol Report", "Patient: Ravi Kumar   Sex: Male   Age: 58 years", "Report date: 12 September 2026", "",
                 "Fasting glucose        148 mg/dL      (70-99)", "HbA1c                  7.1 %          (4.0-5.6)", "Total cholesterol      245 mg/dL      (< 200)",
                 "LDL cholesterol        162 mg/dL      (< 100)", "HDL cholesterol         36 mg/dL      (> 40)", "Triglycerides          240 mg/dL      (< 150)", "Blood pressure: 152/94 mmHg"]
        font = None
        for name in ("consola.ttf", "DejaVuSansMono.ttf", "cour.ttf", "arial.ttf"):
            try:
                font = ImageFont.truetype(name, 26)
                break
            except OSError:
                continue
        font = font or ImageFont.load_default(size=26)
        im = Image.new("RGB", (1100, 60 + 44 * len(lines)), "white")
        d = ImageDraw.Draw(im)
        for i, ln in enumerate(lines):
            d.text((30, 30 + 44 * i), ln, fill=(30, 30, 30), font=font)
        photo = im.rotate(1.2, expand=True, fillcolor="white")
        photo.save(OUT / "F1_photo_of_lab_report.png")
        photo.save(OUT / "F2_scanned_lab_report_image_only.pdf")          # a PDF made only of a picture: there is no text to read, so OCR is used
    except Exception:  # noqa: BLE001
        pass
    (OUT / "README.txt").write_text(README, encoding="utf-8")
    print(f"Wrote {len(list(OUT.iterdir()))} files to {OUT}")
    return 0


README = """PranaSync sample documents (all made up)
=========================================
Register a new account in the portal, open "Upload documents", and add these one at a time. Use ONE person's files per account.

Person A: Ravi Kumar, 58  (add them in this order and watch the three cards grow)
  A1_Ravi_lab_report_blood_sugar_and_cholesterol.pdf   blood sugar and cholesterol -> blood sugar 'Higher' (evidence about 58), heart and blood pressure still thin (evidence about 34 to 42)
  A2_Ravi_clinic_visit_note.pdf                         blood pressure, weight, smoking, family history -> all three areas 'Higher' with evidence at 96 or more
  A4_Ravi_followup_lab_report_2_months_later.pdf       the same tests two months later (12 November): upload it after A1 and Home shows how each value changed, with a small trend line
  A3_Ravi_fitness_tracker_export.csv                    30 days of steps, sleep, heart rate -> evidence reaches 100, the missing list is empty
Person B: B1_Meera_healthy_checkup_report.pdf           one complete report of a healthy 34-year-old -> all three areas 'Lower'
Person C: C1_Sam_blood_sugar_only.docx                  one Word file with only two values -> blood sugar 'Higher', heart 'Not enough information yet', and a list of what is missing
Person D: D1_Priya_lab_report_mmol_units.pdf            values in mmol/L and mmol/mol -> converted to mg/dL and % automatically
Person E: E1_Arun_lab_results.xlsx                      results in an Excel sheet
G1_Full_workup_Kofi_all_values.pdf                      one complete work-up: all three areas get a class, evidence reaches about 100
G2_Unusual_wording_note_AI_second_reader.pdf            a note written in sentences: the pattern reader misses values and the AI second reader adds them (marked 'Read by AI' on the review page)
G3_Range_printed_before_result_review_practice.pdf      the usual range is printed before each result: on the review page check that 131, 6.6, 171... were read, not the range numbers
F1_photo_of_lab_report.png                              a photo of a report: read on this computer by OCR; every value is marked 'Read from an image: please check'
F2_scanned_lab_report_image_only.pdf                    a scanned (picture-only) PDF: no text inside, so OCR reads it the same way

Try also: uploading the same file twice (it is refused as a duplicate) and deleting a document (its values go with it).
"""

if __name__ == "__main__":
    sys.exit(main())
