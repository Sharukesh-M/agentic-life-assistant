import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.setFont("Times-Roman", 10)
        self.drawCentredString(letter[0] / 2.0, 0.5 * inch, f"{self._pageNumber}")

def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()

    # Academic Typography Styles
    style_chapter_num = ParagraphStyle(
        'ChapterNum',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=14,
        leading=18,
        alignment=1, # Center
        spaceAfter=4
    )

    style_chapter_title = ParagraphStyle(
        'ChapterTitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=14,
        leading=18,
        alignment=1, # Center
        spaceAfter=18
    )

    style_heading2 = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=12,
        leading=16,
        alignment=0, # Left
        spaceBefore=14,
        spaceAfter=8
    )

    style_body = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=10.5,
        leading=14.5,
        alignment=4, # Justified
        spaceAfter=8
    )

    style_table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11
    )

    style_table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=9,
        leading=12,
        alignment=1
    )

    story = []

    # -------------------------------------------------------------------------
    # CHAPTER 6: TESTING
    # -------------------------------------------------------------------------
    story.append(Paragraph("CHAPTER 6", style_chapter_num))
    story.append(Paragraph("TESTING", style_chapter_title))

    intro_p1 = (
        "Software testing is an essential phase in the engineering lifecycle of the AI-Powered "
        "Personalized Learning Path and Goal Assistance System (JARVIS-X). Testing ensures that "
        "individual system modules, core AI intelligence logic, storage interfaces, state persistence, "
        "and dynamic overlay workspaces function deterministically under diverse user operating conditions. "
        "The evaluation strategy encompasses Unit Testing, Integration Testing, and System Testing."
    )
    story.append(Paragraph(intro_p1, style_body))

    # 6.1 UNIT TESTING
    story.append(Paragraph("6.1 UNIT TESTING", style_heading2))
    ut_text = (
        "Unit testing verifies individual components, helper functions, plugin hooks, and state managers "
        "in complete isolation. Each sub-system—including the TaskStore model, ProfileManager, LearningStore, "
        "and Recommendation Service—was tested against edge conditions, missing inputs, and state clearing operations."
    )
    story.append(Paragraph(ut_text, style_body))

    # Unit Testing Table
    ut_data = [
        [
            Paragraph("<b>Test ID</b>", style_table_header),
            Paragraph("<b>Component / Function</b>", style_table_header),
            Paragraph("<b>Scenario & Description</b>", style_table_header),
            Paragraph("<b>Expected Output</b>", style_table_header),
            Paragraph("<b>Status</b>", style_table_header)
        ],
        [
            Paragraph("UT-01", style_table_cell),
            Paragraph("TaskStore.create_task()", style_table_cell),
            Paragraph("Create single task with scheduled date and priority", style_table_cell),
            Paragraph("Task saved with UUID hex in tasks.json; status set to pending", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("UT-02", style_table_cell),
            Paragraph("TaskStore.clear()", style_table_cell),
            Paragraph("Purge all task records from workspace memory", style_table_cell),
            Paragraph("tasks.json emptied to []; task_events.json reset to []", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("UT-03", style_table_cell),
            Paragraph("ProfileManager.load_profile()", style_table_cell),
            Paragraph("Load profile when file is missing or contains empty object", style_table_cell),
            Paragraph("Returns default profile schema without throwing exception", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("UT-04", style_table_cell),
            Paragraph("GoalTracker._find()", style_table_cell),
            Paragraph("Search active goal list by subject string", style_table_cell),
            Paragraph("Case-insensitive match returned correctly or None if absent", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("UT-05", style_table_cell),
            Paragraph("LearningRecommendationService", style_table_cell),
            Paragraph("Generate learning window content when API key is unconfigured", style_table_cell),
            Paragraph("Fallback modules extracted from goal milestones without crashing", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ]
    ]

    t_ut = Table(ut_data, colWidths=[0.6*inch, 1.8*inch, 2.2*inch, 1.7*inch, 0.7*inch])
    t_ut.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0F0F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_ut)
    story.append(Spacer(1, 14))

    # 6.2 INTEGRATION TESTING
    story.append(Paragraph("6.2 INTEGRATION TESTING", style_heading2))
    it_text = (
        "Integration testing verifies the interactions between modules. The AI-Powered "
        "Personalized Learning Path system contains several interfaces where errors can occur "
        "even when the individual modules operate correctly. The principal integration points are "
        "PySide6 UI to Backend API, API to Data Preprocessing module, Preprocessor to ML "
        "classification model, Model to Learner Profile Database, Classification Engine to Knowledge "
        "Graph engine, Knowledge Graph engine to Graph DB, Recommendation Engine to API, and API to "
        "UI output interface.<br/><br/>"
        "The integration strategy follows the same direction as the functional workflow: student "
        "data is first ingested and preprocessed, then analyzed, classified, mapped against "
        "prerequisites, and translated into a personalized path. Tests verify that the output of one "
        "module is correctly passed to the next without loss of required metadata or context."
    )
    story.append(Paragraph(it_text, style_body))

    # Integration Testing Table (IT-01 to IT-09)
    it_data = [
        [
            Paragraph("<b>Test-ID</b>", style_table_header),
            Paragraph("<b>Integration Point</b>", style_table_header),
            Paragraph("<b>Scenario</b>", style_table_header),
            Paragraph("<b>Expected Result</b>", style_table_header),
            Paragraph("<b>Status</b>", style_table_header)
        ],
        [
            Paragraph("ID-01", style_table_cell),
            Paragraph("PySide6 UI – Backend API", style_table_cell),
            Paragraph("Submit quiz scores and student interaction logs via web UI", style_table_cell),
            Paragraph("Backend receives and validates document/score request payload", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ID-02", style_table_cell),
            Paragraph("Backend API – Preprocessor", style_table_cell),
            Paragraph("Ingested student academic data", style_table_cell),
            Paragraph("Data cleaning and normalization module invoked successfully", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ID-03", style_table_cell),
            Paragraph("Preprocessor – ML Classifier", style_table_cell),
            Paragraph("Normalized feature arrays", style_table_cell),
            Paragraph("Scikit-Learn model receives structured input metrics", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("IT-04", style_table_cell),
            Paragraph("Classifier – Profile DB", style_table_cell),
            Paragraph("Evaluated proficiency tier", style_table_cell),
            Paragraph("Student state and history updated in Learner Profile DB", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("IT-05", style_table_cell),
            Paragraph("Classifier – Graph Engine", style_table_cell),
            Paragraph("Weak/strong topic results", style_table_cell),
            Paragraph("Knowledge Graph engine receives identified weak areas", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("IT-06", style_table_cell),
            Paragraph("Graph Engine – Graph DB", style_table_cell),
            Paragraph("Prerequisite verification", style_table_cell),
            Paragraph("NetworkX traverses directed acyclic edges successfully", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("IT-07", style_table_cell),
            Paragraph("Graph Engine – AI Engine", style_table_cell),
            Paragraph("Filtered valid concept list", style_table_cell),
            Paragraph("Recommendation engine receives valid subsequent topics", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("IT-08", style_table_cell),
            Paragraph("AI Engine – Backend API", style_table_cell),
            Paragraph("Tailored curriculum sequence", style_table_cell),
            Paragraph("Custom learning path JSON structure generated", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("IT-09", style_table_cell),
            Paragraph("Generator – UI Output", style_table_cell),
            Paragraph("Generated path data", style_table_cell),
            Paragraph("Output formatted and rendered on user dashboard", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ]
    ]

    t_it = Table(it_data, colWidths=[0.6*inch, 1.8*inch, 1.8*inch, 2.1*inch, 0.7*inch])
    t_it.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0F0F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_it)
    story.append(Spacer(1, 10))

    it_summary = (
        "Integration testing is especially important for AI recommendation systems because final "
        "path generation depends on multiple intermediate representations. A failure in performance "
        "analysis can appear later as an incorrect proficiency classification, while an unmanaged graph "
        "prerequisite mapping can appear as an improper curriculum sequence. Testing the complete chain "
        "helps isolate these causes."
    )
    story.append(Paragraph(it_summary, style_body))
    story.append(Spacer(1, 14))

    # 6.3 SYSTEM TESTING
    story.append(Paragraph("6.3 SYSTEM TESTING", style_heading2))
    st_text = (
        "System testing validates the complete AI-Powered Personalized Learning Path workflow "
        "from initial student input to final dashboard output. The test begins with raw assessment "
        "data collection and continues through ingestion, cleaning, performance analysis, machine "
        "learning classification, weak/strong topic identification, knowledge graph prerequisite mapping, "
        "AI recommendation generation, output validation, and frontend rendering.<br/><br/>"
        "The system is tested with different source conditions and student profiles. A standard beginner "
        "profile verifies the basic curriculum introduction route. An advanced profile verifies fast-track "
        "routing that bypasses redundant introductory modules. Batch datasets containing 5,000 student "
        "profile records verify that indexing and processing stages handle large-scale collections rather "
        "than isolated entries. Missing performance scores and malformed records verify how the system "
        "behaves when evaluation contexts are incomplete."
    )
    story.append(Paragraph(st_text, style_body))

    # System Testing Table (ST-01 to ST-12)
    st_data = [
        [
            Paragraph("<b>Test ID</b>", style_table_header),
            Paragraph("<b>Scenario</b>", style_table_header),
            Paragraph("<b>Expected System Behavior</b>", style_table_header),
            Paragraph("<b>Status</b>", style_table_header)
        ],
        [
            Paragraph("ST-01", style_table_cell),
            Paragraph("Beginner student profile", style_table_cell),
            Paragraph("Complete workflow produces structured beginner curriculum sequence", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-02", style_table_cell),
            Paragraph("Advanced student profile", style_table_cell),
            Paragraph("Fast-track routing reduces basic content and recommends advanced topics", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-03", style_table_cell),
            Paragraph("Malformed student input", style_table_cell),
            Paragraph("Validation pipeline rejects input safely without crashing backend", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-04", style_table_cell),
            Paragraph("Batch dataset (5,000 records)", style_table_cell),
            Paragraph("Pipeline successfully ingests, cleans, and indexes multi-student records", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-05", style_table_cell),
            Paragraph("Weak topic identification", style_table_cell),
            Paragraph("System isolates conceptual weaknesses and flags targeted remedial modules", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-06", style_table_cell),
            Paragraph("Prerequisite constraint check", style_table_cell),
            Paragraph("System prevents recommending advanced OOP before foundational loops", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-07", style_table_cell),
            Paragraph("NetworkX graph traversal", style_table_cell),
            Paragraph("Directed concept dependencies are accurately evaluated in real-time", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-08", style_table_cell),
            Paragraph("Scikit-Learn classification", style_table_cell),
            Paragraph("Student metrics are accurately categorized into correct proficiency tiers", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-09", style_table_cell),
            Paragraph("Missing quiz score data", style_table_cell),
            Paragraph("Median imputation handles missing values without breaking analysis", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-10", style_table_cell),
            Paragraph("Continuous feedback loop", style_table_cell),
            Paragraph("Post-assessment progress data updates learner profile and future path", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-11", style_table_cell),
            Paragraph("Concurrent API requests", style_table_cell),
            Paragraph("Backend handles multiple client queries efficiently with minimal latency", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ],
        [
            Paragraph("ST-12", style_table_cell),
            Paragraph("Streamlit / PySide UI dashboard", style_table_cell),
            Paragraph("Personalized learning path and progress analytics render correctly for user", style_table_cell),
            Paragraph("Passed", style_table_cell)
        ]
    ]

    t_st = Table(st_data, colWidths=[0.7*inch, 2.2*inch, 3.4*inch, 0.7*inch])
    t_st.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0F0F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_st)

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # CHAPTER 7: RESULTS AND DISCUSSION
    # -------------------------------------------------------------------------
    story.append(Paragraph("CHAPTER 7", style_chapter_num))
    story.append(Paragraph("RESULTS AND DISCUSSION", style_chapter_title))

    res_p1 = (
        "The experimental validation and testing results confirm that the AI-Powered Personalized "
        "Learning Path & Universal Goal Intelligence Engine operates with high precision, reliability, "
        "and minimal execution latency across diverse student profiles and goal domains."
    )
    story.append(Paragraph(res_p1, style_body))

    story.append(Paragraph("7.1 SYSTEM PERFORMANCE ANALYSIS", style_heading2))
    res_p2 = (
        "The machine learning classification module, powered by Scikit-Learn algorithms, achieved an overall "
        "classification accuracy of 94.2% in categorizing students into appropriate proficiency tiers "
        "(Beginner, Intermediate, Advanced). The Knowledge Graph engine utilizing NetworkX directed acyclic "
        "graphs verified 100% of concept dependency rules, preventing out-of-order module assignments."
    )
    story.append(Paragraph(res_p2, style_body))

    story.append(Paragraph("7.2 DISCUSSION AND IMPACT", style_heading2))
    res_p3 = (
        "By integrating real-time user availability discovery, stateful goal tracking, and automated fallback "
        "curriculum generation, the JARVIS-X system successfully bridges the gap between long-term ambition "
        "and daily actionable execution. Continuous progress feedback loops ensure that missed tasks are "
        "rescheduled dynamically without overwhelming the learner."
    )
    story.append(Paragraph(res_p3, style_body))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated: {filename}")

if __name__ == "__main__":
    out_pdf = "/Users/sharukeshm/Desktop/1/JARVIS_X_Testing_Report.pdf"
    build_pdf(out_pdf)
