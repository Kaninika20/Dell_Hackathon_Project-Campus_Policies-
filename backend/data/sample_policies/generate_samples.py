from __future__ import annotations

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def create_sample_academic_integrity_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e3a8a')
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1f2937'),
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#374151')
    )
    notice_style = ParagraphStyle(
        'Notice',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#dc2626')
    )

    story = [
        Paragraph("CAMPUS POLICY: ACADEMIC INTEGRITY CODE", title_style),
        Paragraph("<b>[DEMO NOTICE: This is a SAMPLE fictional document created for software demonstration purposes only. It does not represent genuine university regulations.]</b>", notice_style),
        Spacer(1, 14),
        Paragraph("SECTION 1. PURPOSE AND APPLICABILITY", heading_style),
        Paragraph("This policy governs academic honesty standards for all enrolled undergraduate and postgraduate students. The university requires strict adherence to original academic scholarship, proper citation practices, and ethical conduct during all evaluations, examinations, and laboratory assignments.", body_style),
        Spacer(1, 10),
        Paragraph("SECTION 2. DEFINITION OF PLAGIARISM", heading_style),
        Paragraph("Plagiarism is defined as the submission, reproduction, or inclusion of words, ideas, code, designs, or data created by others without explicit and accurate citation. This includes both direct verbatim copying and paraphrasing without proper attribution.", body_style),
        Paragraph("Use of generative artificial intelligence tools without instructor authorization is considered an unauthorized collaboration violation under Subsection 2.4.", body_style),
        Spacer(1, 10),
        PageBreak(),  # Ensure multi-page document
        Paragraph("SECTION 3. INVESTIGATION PROCEDURES", heading_style),
        Paragraph("Upon identifying suspected misconduct, the course instructor must notify the student in writing within five (5) academic working days. A preliminary departmental conference shall be scheduled to review submitted evidence.", body_style),
        Spacer(1, 10),
        Paragraph("SECTION 4. SANCTIONS AND PENALTIES", heading_style),
        Paragraph("Sanctions are determined based on the severity and recurrence of the infraction. Minor first-time infractions may result in a formal written reprimand and a grade of zero (0) on the assessment. Severe or repeated violations will result in course failure (Grade XF) or immediate academic suspension for one full academic semester.", body_style),
        Spacer(1, 10),
        Paragraph("SECTION 5. APPEALS PROCESS", heading_style),
        Paragraph("Students may file an appeal to the Academic Review Board within ten (10) calendar days of receiving a written sanctions decision. Grounds for appeal are limited to procedural irregularity, newly discovered evidence, or disproportionate sanction severity.", body_style)
    ]
    doc.build(story)


def create_sample_attendance_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#065f46')
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1f2937'),
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#374151')
    )
    notice_style = ParagraphStyle(
        'Notice',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#dc2626')
    )

    story = [
        Paragraph("CAMPUS POLICY: STUDENT ATTENDANCE AND LEAVE RULES", title_style),
        Paragraph("<b>[DEMO NOTICE: This is a SAMPLE fictional document created for software demonstration purposes only. It does not represent genuine university regulations.]</b>", notice_style),
        Spacer(1, 14),
        Paragraph("RULE 1. MINIMUM ATTENDANCE THRESHOLD", heading_style),
        Paragraph("All regular full-time students must maintain a minimum attendance of seventy-five percent (75%) in every registered theoretical and laboratory subject across the semester.", body_style),
        Spacer(1, 10),
        Paragraph("RULE 2. CONDONATION OF ATTENDANCE SHORTAGE", heading_style),
        Paragraph("Shortage of attendance between sixty-five percent (65%) and seventy-four percent (74%) may be condoned by the Dean of Student Affairs exclusively on genuine medical grounds supported by a certified medical practitioner certificate submitted within three (3) days of resuming classes.", body_style),
        Spacer(1, 10),
        Paragraph("RULE 3. CONSEQUENCES OF ATTENDANCE DEFICIT", heading_style),
        Paragraph("Students whose final attendance falls below sixty-five percent (65%) shall be detained from sitting for end-semester examinations in that specific course and must re-register the course during the subsequent academic cycle.", body_style)
    ]
    doc.build(story)


if __name__ == "__main__":
    out_dir = Path("c:/Users/milan/OneDrive/Desktop/Dell_Hackathon_Project/backend/data/sample_policies")
    out_dir.mkdir(parents=True, exist_ok=True)
    create_sample_academic_integrity_pdf(out_dir / "SAMPLE_Academic_Integrity_Policy.pdf")
    create_sample_attendance_pdf(out_dir / "SAMPLE_Attendance_And_Leave_Rules.pdf")
    print("Sample policies generated successfully.")

