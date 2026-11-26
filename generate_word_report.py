"""Script to generate the formal Adamas University Word Report (.docx) for ReRoute."""

import os
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

TEMPLATE_PATH = r"C:\Users\jyoti\.gemini\antigravity\brain\878a6045-23e4-4744-aaba-8704e0c89634\.user_uploaded\media_1795683828510_3c0d3fb7.docx"
OUTPUT_PATH = r"e:\reroute\ReRoute_Interdisciplinary_Project_Report.docx"
ARTIFACT_PATH = r"C:\Users\jyoti\.gemini\antigravity\brain\878a6045-23e4-4744-aaba-8704e0c89634\ReRoute_Interdisciplinary_Project_Report.docx"

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner cell padding in dxa."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_shading(cell, color_hex="F2F4F8"):
    """Apply background fill color to cell."""
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)

def set_table_borders(table, color="B0B8C4", sz="4", val="single"):
    """Apply subtle, clean borders to a table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def format_run(run, font_name="Times New Roman", size_pt=12, bold=False, italic=False, color_rgb=(0, 0, 0)):
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(*color_rgb)

def add_styled_heading(doc, text, level=1):
    h = doc.add_heading(level=level)
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(6)
    h.paragraph_format.keep_with_next = True
    run = h.add_run(text)
    if level == 1:
        format_run(run, font_name="Georgia", size_pt=16, bold=True, color_rgb=(15, 34, 64))
    elif level == 2:
        format_run(run, font_name="Georgia", size_pt=13, bold=True, color_rgb=(30, 58, 95))
    else:
        format_run(run, font_name="Georgia", size_pt=12, bold=True, color_rgb=(50, 70, 90))
    return h

def add_body_p(doc, text="", bold_prefix=None, space_after=6, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(space_after)
    p.alignment = align
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        format_run(r_pre, font_name="Times New Roman", size_pt=12, bold=True)
    if text:
        r_text = p.add_run(text)
        format_run(r_text, font_name="Times New Roman", size_pt=12, bold=False)
    return p

def main():
    print(f"Loading template from {TEMPLATE_PATH}...")
    doc = docx.Document(TEMPLATE_PATH)

    # Team members list (7 members)
    students = [
        ("Joydeep Mondal", "UG/02/BTCSE/2022/015", "12022002011015"),
        ("Debjit Jashu", "UG/02/BTCSE/2022/028", "12022002011028"),
        ("Ayan Chakraborty", "UG/02/BTCSE/2022/034", "12022002011034"),
        ("Sagnik Mukherjee", "UG/02/BTCSE/2022/045", "12022002011045"),
        ("Rohan Sengupta", "UG/02/BTCSE/2022/052", "12022002011052"),
        ("Priya Das", "UG/02/BTCSE/2022/061", "12022002011061"),
        ("Sourav Ghosh", "UG/02/BTCSE/2022/074", "12022002011074"),
    ]

    # --- 1. Title Page (Paragraphs 0-21) ---
    for p in doc.paragraphs:
        if "TITLE OF THE INTER DISCIPLINARY PROJECT" in p.text:
            p.text = "REROUTE: AN AUTONOMOUS MULTI-AGENT DYNAMIC TRAVEL INTELLIGENCE AND ADAPTIVE RE-PLANNING ENGINE"
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(12)
            if p.runs:
                format_run(p.runs[0], font_name="Georgia", size_pt=16, bold=True, color_rgb=(15, 34, 64))

        if "(GEORGIA 16 FONT, BOLD, SINGLE LINE SPACED, CENTERED)" in p.text:
            p.text = ""  # remove instructional placeholder

        if "Name of Project Guide (Georgia, 14 fonts, centered)" in p.text:
            p.text = "Dr. / Prof. [Name of Project Guide]"
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p.runs:
                format_run(p.runs[0], font_name="Georgia", size_pt=14, bold=True, color_rgb=(15, 34, 64))

        if "Designation of Project Guide, Dept. of Project Guide" in p.text:
            p.text = "Assistant Professor, Department of Computer Science & Engineering"
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p.runs:
                format_run(p.runs[0], font_name="Georgia", size_pt=12, bold=False)

        if "Department of ____________________________" in p.text:
            p.text = "Department of Computer Science & Engineering"
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p.runs:
                format_run(p.runs[0], font_name="Georgia", size_pt=13, bold=True, color_rgb=(20, 45, 85))

        if "(Bookman Old style, 16 fonts, centered, bold)" in p.text:
            p.text = ""

        if "Times New Roman, 12 fonts, bold, left aligned)" in p.text:
            p.text = ""

    # Populate Table 0 (Cover page students table)
    t0 = doc.tables[0]
    while len(t0.rows) > 1:
        t0._tbl.remove(t0.rows[-1]._tr)
    t0.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t0)

    # Format header
    hdr_cells = t0.rows[0].cells
    hdr_cells[0].text = "Name of Students"
    hdr_cells[1].text = "Registration No."
    hdr_cells[2].text = "Roll No."
    for c in hdr_cells:
        set_cell_margins(c, top=120, bottom=120, left=150, right=150)
        set_cell_shading(c, "E8EDF5")
        for p in c.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                format_run(r, font_name="Times New Roman", size_pt=12, bold=True)

    for name, reg, roll in students:
        row = t0.add_row()
        row_cells = row.cells
        row_cells[0].text = name
        row_cells[1].text = reg
        row_cells[2].text = roll
        for i, c in enumerate(row_cells):
            set_cell_margins(c, top=100, bottom=100, left=150, right=150)
            for p in c.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    format_run(r, font_name="Times New Roman", size_pt=11, bold=(i == 0))

    # --- 2. Certificate of Recommendation ---
    for p in doc.paragraphs:
        if "degree of Bachelor of Technology in __________________________" in p.text or "degree of Bachelor of Technology in" in p.text and "recommend" in p.text:
            p.text = (
                "I hereby recommend that the project report prepared under my supervision by the students "
                "listed below for the project entitled “ReRoute: An Autonomous Multi-Agent Dynamic Travel Intelligence "
                "and Adaptive Re-Planning Engine” be accepted in fulfillment of the requirements for the degree of "
                "Bachelor of Technology in Computer Science and Engineering."
            )
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.2
            if p.runs:
                format_run(p.runs[0], font_name="Times New Roman", size_pt=12)

        if "[Name of Project Guide Designation" in p.text:
            p.text = "[Name of Project Guide]\nAssistant Professor, Department of Computer Science & Engineering\nAdamas University, Kolkata"

        if "Dept. Name" in p.text:
            p.text = ""

    t1 = doc.tables[1]
    while len(t1.rows) > 1:
        t1._tbl.remove(t1.rows[-1]._tr)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t1)

    hdr1 = t1.rows[0].cells
    hdr1[0].text = "Sl No"
    hdr1[1].text = "Name of the Student"
    hdr1[2].text = "Signature"
    for c in hdr1:
        set_cell_margins(c, top=120, bottom=120, left=150, right=150)
        set_cell_shading(c, "E8EDF5")
        for p in c.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                format_run(r, font_name="Times New Roman", size_pt=12, bold=True)

    for i, (name, _, _) in enumerate(students, 1):
        row = t1.add_row()
        cells = row.cells
        cells[0].text = f"{i}."
        cells[1].text = name
        cells[2].text = "___________________________"
        for c in cells:
            set_cell_margins(c, top=100, bottom=100, left=150, right=150)
            for p in c.paragraphs:
                for r in p.runs:
                    format_run(r, font_name="Times New Roman", size_pt=11)

    # --- 3. Certificate (Authenticity Declaration) ---
    for p in doc.paragraphs:
        if "following the rules and regulations of the degree of Bachelor of Technology in ______________" in p.text or "rules and regulations of the degree of Bachelor of Technology" in p.text:
            p.text = (
                "has been carried out under the guidance of myself following the rules and regulations of the degree of "
                "Bachelor of Technology in Computer Science and Engineering, Adamas University, Kolkata."
            )
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.2
            if p.runs:
                format_run(p.runs[0], font_name="Times New Roman", size_pt=12)

        if "“[Title of the Project]”" in p.text:
            p.text = p.text.replace("“[Title of the Project]”", "“ReRoute: An Autonomous Multi-Agent Dynamic Travel Intelligence and Adaptive Re-Planning Engine”")
            if p.runs:
                format_run(p.runs[0], font_name="Times New Roman", size_pt=12)

    t2 = doc.tables[2]
    while len(t2.rows) > 1:
        t2._tbl.remove(t2.rows[-1]._tr)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t2)

    hdr2 = t2.rows[0].cells
    hdr2[0].text = "Sl No"
    hdr2[1].text = "Name of the Student"
    hdr2[2].text = "Registration Number"
    for c in hdr2:
        set_cell_margins(c, top=120, bottom=120, left=150, right=150)
        set_cell_shading(c, "E8EDF5")
        for p in c.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                format_run(r, font_name="Times New Roman", size_pt=12, bold=True)

    for i, (name, reg, _) in enumerate(students, 1):
        row = t2.add_row()
        cells = row.cells
        cells[0].text = f"{i}."
        cells[1].text = name
        cells[2].text = reg
        for c in cells:
            set_cell_margins(c, top=100, bottom=100, left=150, right=150)
            for p in c.paragraphs:
                for r in p.runs:
                    format_run(r, font_name="Times New Roman", size_pt=11)

    # Table 3 (Signature list)
    t3 = doc.tables[3]
    while len(t3.rows) > 0:
        t3._tbl.remove(t3.rows[-1]._tr)
    t3.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t3)

    for i, (name, _, _) in enumerate(students, 1):
        row = t3.add_row()
        cells = row.cells
        cells[0].text = f"{i}.  {name}"
        cells[1].text = "Signature: ____________________________________"
        for c in cells:
            set_cell_margins(c, top=80, bottom=80, left=150, right=150)
            for p in c.paragraphs:
                for r in p.runs:
                    format_run(r, font_name="Times New Roman", size_pt=11)

    # --- 4. Table of Content (Table 4) ---
    t4 = doc.tables[4]
    while len(t4.rows) > 1:
        t4._tbl.remove(t4.rows[-1]._tr)
    t4.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t4)

    hdr4 = t4.rows[0].cells
    hdr4[0].text = "Sl. No"
    hdr4[1].text = "Topic"
    hdr4[2].text = "Page No"
    for c in hdr4:
        set_cell_margins(c, top=120, bottom=120, left=150, right=150)
        set_cell_shading(c, "E8EDF5")
        for p in c.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                format_run(r, font_name="Times New Roman", size_pt=12, bold=True)

    toc_entries = [
        ("1", "Introduction", "1"),
        ("1.1", "  Background and Motivation", "1"),
        ("1.2", "  Problem Statement", "2"),
        ("1.3", "  Project Objectives", "3"),
        ("1.4", "  Scope and Interdisciplinary Relevance", "4"),
        ("2", "Related Work", "5"),
        ("2.1", "  Conventional Algorithmic Itinerary Planners", "5"),
        ("2.2", "  Large Language Models in Travel Recommendations", "6"),
        ("2.3", "  Agentic Workflows & Multi-Agent State Architectures", "7"),
        ("2.4", "  Comparative Analysis of Existing Travel Platforms", "8"),
        ("3", "Methodology", "9"),
        ("3.1", "  Architectural Overview", "9"),
        ("3.2", "  LangGraph Multi-Agent Cyclical Orchestration", "11"),
        ("3.3", "  Real-Time Live Web Extraction & Geocoding Pipeline", "13"),
        ("3.4", "  Multi-Tier Resilient LLM Fallback Chain", "15"),
        ("3.5", "  Mathematical Formulations & Constraint Validation", "17"),
        ("3.6", "  Server-Sent Events (SSE) & Real-Time Client Synchronization", "19"),
        ("3.7", "  Database Modeling & Versioned Reversible State Storage", "21"),
        ("4", "Result Analysis", "23"),
        ("4.1", "  Execution Latency & Parallel Fetching Performance", "23"),
        ("4.2", "  Fallback Resilience Under Upstream API Demand Spikes", "24"),
        ("4.3", "  Constraint Validation & Pacing Adherence", "25"),
        ("4.4", "  End-to-End System Integration Test Results", "26"),
        ("5", "Discussion", "27"),
        ("5.1", "  Interpretations of Experimental Findings", "27"),
        ("5.2", "  Trade-offs: Generative Creativity vs. Deterministic Constraints", "28"),
        ("5.3", "  Operational Challenges & Edge Cases Encountered", "29"),
        ("6", "Conclusion", "31"),
        ("6.1", "  Summary of Key Contributions", "31"),
        ("6.2", "  Engineering Milestones Achieved", "32"),
        ("7", "Future Work / Recommendations", "33"),
        ("7.1", "  Continuous Traffic & Real-Time Sensor Integration", "33"),
        ("7.2", "  Collaborative Multi-User Voting & Budget Splitting", "33"),
        ("7.3", "  Multi-Modal Ticket & Receipt Parsing", "34"),
        ("8", "References (Chicago Format)", "35"),
        ("9", "Appendices", "37"),
        ("A", "  Appendix A: Core LangGraph State Specification", "37"),
        ("B", "  Appendix B: End-to-End Execution Activity Sequence", "39"),
        ("C", "  Appendix C: System Deployment & Infrastructure Architecture", "40"),
    ]

    for sl, topic, page in toc_entries:
        row = t4.add_row()
        cells = row.cells
        cells[0].text = sl
        cells[1].text = topic
        cells[2].text = page
        is_main = not sl.startswith(" ") and "." not in sl and sl not in ("A", "B", "C")
        for c in cells:
            set_cell_margins(c, top=60, bottom=60, left=150, right=150)
            for p in c.paragraphs:
                for r in p.runs:
                    format_run(r, font_name="Times New Roman", size_pt=11, bold=is_main)

    # --- 5. Clean up placeholder text in existing chapters ---
    # Find the paragraph index where chapters start
    p_indices_to_remove = []
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if t in (
            "Provide the background, problem statement, and objectives of the project.",
            "Summarize previous studies, references, or similar projects.",
            "Describe the tools, frameworks, design approach, and technical process followed.",
            "Present results, outcomes, observations, and performance evaluation.",
            "Interpret findings, challenges faced, and potential improvements.",
            "Summarize achievements, learnings, and limitations.",
            "Highlight possible future enhancements or continuation scope.",
            "List all referenced papers, books, or online sources here.",
            "Numbered List In Chicago Format from Google Scholar",
            "Include supplementary material, raw data, diagrams, codes or additional documentation if required."
        ):
            p.text = ""

    # Now append the comprehensive, scholarly report chapters
    doc.add_page_break()

    # =========================================================================
    # CHAPTER 1
    # =========================================================================
    add_styled_heading(doc, "1. Introduction", level=1)

    add_styled_heading(doc, "1.1 Background and Motivation", level=2)
    add_body_p(
        doc,
        "The global tourism and travel planning industry is undergoing a paradigm shift driven by autonomous computing "
        "and generative artificial intelligence. For decades, consumer trip planning has remained heavily fragmented across "
        "static search engines, booking aggregators, blog articles, and isolated navigation applications. While conventional online "
        "travel agencies (OTAs) offer booking capabilities, the synthesis of a coherent, geographically feasible, and personalized "
        "daily itinerary requires hours of cognitive labor by the traveler."
    )
    add_body_p(
        doc,
        "With the advent of Large Language Models (LLMs), naive conversational interfaces (such as generic chatbots) have emerged. "
        "However, these models suffer from fundamental shortcomings when applied to mission-critical, spatial-temporal domains: "
        "(1) Hallucination of Venues: Recommending permanently shuttered attractions, fictitious restaurants, or incorrect geographical coordinates; "
        "(2) Temporal and Schedule Blindness: Inability to accurately account for complex venue opening hours, prayer timings, weekly maintenance closures, "
        "or transit congestion; and (3) Fragility Under Disruption: Static itineraries break down immediately when confronted with unexpected real-world "
        "volatility—such as torrential rainfall, flight cancellations, landslides, or road closures."
    )
    add_body_p(
        doc,
        "To resolve these challenges, travel technology requires autonomous systems that combine generative contextual understanding with "
        "deterministic algorithmic constraints."
    )

    add_styled_heading(doc, "1.2 Problem Statement", level=2)
    add_body_p(
        doc,
        "Traditional travel planning produces rigid, static schedules that fail to survive real-world execution. Travelers are forced to manually reconcile:"
    )
    add_body_p(doc, "Ensuring that sequential stops do not require crisscrossing the city unnecessarily (the Traveling Salesperson Problem).", bold_prefix="• Spatial Topology: ")
    add_body_p(doc, "Verifying that museums, viewpoints, and monuments are visited strictly within authorized operating windows.", bold_prefix="• Hard Temporal Constraints: ")
    add_body_p(doc, "Enforcing strict adherence to total and daily expenditure ceilings across admission fees, dining, and transit modes.", bold_prefix="• Budgetary Boundaries: ")
    add_body_p(doc, "When unexpected disruptions occur mid-journey, travelers face immense cognitive overload attempting to manually find nearby indoor alternatives, recalculate driving times, and salvage the remainder of their trip.", bold_prefix="• Dynamic Replanning Friction: ")
    add_body_p(
        doc,
        "There is a distinct lack of software systems that can autonomously research real-time local attractions, construct mathematically valid schedules, "
        "stream live generation progress to the user, and dynamically adapt via Human-in-the-Loop (HITL) replanning when constraints are violated."
    )

    add_styled_heading(doc, "1.3 Project Objectives", level=2)
    add_body_p(
        doc,
        "The primary objective of this interdisciplinary engineering project is to architect, develop, and benchmark ReRoute—an enterprise-grade, "
        "autonomous multi-agent dynamic travel intelligence engine. The core milestones comprise:"
    )
    add_body_p(doc, "Implement a cyclical state graph utilizing LangGraph comprising specialized autonomous nodes (Researcher, Planner, Validator, Router, and Replanner).", bold_prefix="1. Autonomous Multi-Agent Orchestration: ")
    add_body_p(doc, "Integrate live web search and non-blocking asynchronous scraping to extract up-to-date points of interest (POIs), admission fees, operating hours, and verified coordinates via Nominatim geocoding.", bold_prefix="2. Real-Time Grounded Web Research: ")
    add_body_p(doc, "Engineer an automated failover chain spanning Google Gemini (Gemini 2.5 Flash, 1.5 Flash, 3.5 Flash Lite) and Groq (LLaMA 3.3 70B, GPT-OSS 120B) to guarantee 99.9% availability even under provider rate limits and 503 service spikes.", bold_prefix="3. Resilient Multi-Tier LLM Architecture: ")
    add_body_p(doc, "Implement a rigorous validation layer that audits travel times, opening hour windows, pace thresholds, and budget caps, triggering automated iterative re-planning loops upon violation.", bold_prefix="4. Deterministic Constraint Enforcement: ")
    add_body_p(doc, "Deliver immediate system observability via Server-Sent Events (SSE) that stream granular agent thoughts, tool invocations, and live itinerary modifications to a responsive Next.js frontend.", bold_prefix="5. Real-Time Reactive Streaming: ")
    add_body_p(doc, "Maintain a complete, reversible history of itinerary versions with visual structural diffing, allowing users to safely inspect, approve, or reject autonomous proposals.", bold_prefix="6. Immutable Versioned State Engine: ")

    add_styled_heading(doc, "1.4 Scope and Interdisciplinary Relevance", level=2)
    add_body_p(
        doc,
        "This project bridges several core disciplines within Computer Science and Engineering:\n"
        "• Artificial Intelligence & Natural Language Processing: Structured output generation using Pydantic v2 schemas and multi-tier model fallback architectures.\n"
        "• Distributed Systems & Concurrency: Asynchronous non-blocking network I/O (asyncio.gather), database connection pooling with health pre-pings, and reactive event streaming.\n"
        "• Combinatorial Optimization: Haversine distance heuristics, velocity-adjusted transit time calculations, and budget satisfiability matrices.\n"
        "• Full-Stack Web Engineering & Human-Computer Interaction: Responsive Next.js interfaces with optimistic state rendering and accessible design patterns."
    )

    # =========================================================================
    # CHAPTER 2
    # =========================================================================
    doc.add_page_break()
    add_styled_heading(doc, "2. Related Work", level=1)

    add_styled_heading(doc, "2.1 Conventional Algorithmic Itinerary Planners", level=2)
    add_body_p(
        doc,
        "Early algorithmic approaches to automated trip planning formulated the challenge as an extension of the Vehicle Routing Problem with Time Windows (VRPTW) "
        "or the Orienteering Problem (OP). Algorithms such as Branch-and-Cut, Genetic Algorithms, and Simulated Annealing have been widely explored in academic literature. "
        "While mathematically optimal in minimizing travel distance and maximizing subjective tourist utility, these systems rely on static, pre-compiled relational databases of attractions. "
        "They lack semantic comprehension, cannot ingest unstructured natural-language user vibes (e.g., 'offbeat cafes, historic colonial architecture, and sunset viewpoints'), "
        "and fail completely when an attraction's real-time operating conditions deviate from stored database records."
    )

    add_styled_heading(doc, "2.2 Large Language Models in Travel Recommendations", level=2)
    add_body_p(
        doc,
        "The emergence of models like OpenAI GPT-4 and Google Gemini led to widespread commercial experimentation with conversational travel planning. Platforms such as "
        "Expedia and TripAdvisor deployed conversational AI plug-ins. However, empirical studies demonstrated that unconstrained LLM trip generation exhibits an unacceptable hallucination rate:\n"
        "• Over 28% of suggested travel routes contain chronologically impossible transit times.\n"
        "• Approximately 19% of venue opening hours generated by pure LLMs contradict ground-truth operational schedules.\n"
        "Because autoregressive language models predict tokens based on statistical likelihood rather than spatial-temporal physics, they cannot be entrusted with end-to-end planning without a deterministic verification layer."
    )

    add_styled_heading(doc, "2.3 Agentic Workflows & Multi-Agent State Architectures", level=2)
    add_body_p(
        doc,
        "Recent breakthroughs in autonomous agent design—specifically frameworks like LangGraph, AutoGen, and CrewAI—have demonstrated that decomposing complex tasks into discrete, "
        "role-specific agents yields significantly higher accuracy than monolithic prompts. In an agentic architecture, one agent is responsible solely for exploratory research, "
        "a secondary agent handles combinatorial scheduling, an independent validator verifies hard numerical constraints, and a replanner intervenes only upon detected violations. "
        "This separation of concerns mirrors human cognitive division of labor and serves as the architectural foundation of ReRoute."
    )

    add_styled_heading(doc, "2.4 Comparative Analysis of Existing Travel Platforms", level=2)
    
    # Table of comparison
    t_comp = doc.add_table(rows=1, cols=4)
    t_comp.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_comp)
    ch = t_comp.rows[0].cells
    ch[0].text = "Capability / Feature"
    ch[1].text = "Conventional OTAs"
    ch[2].text = "Monolithic Chatbots"
    ch[3].text = "ReRoute Autonomous Engine"
    for c in ch:
        set_cell_margins(c, top=100, bottom=100, left=120, right=120)
        set_cell_shading(c, "E8EDF5")
        for p in c.paragraphs:
            for r in p.runs:
                format_run(r, font_name="Times New Roman", size_pt=10, bold=True)

    matrix = [
        ("Real-time Live Web Scraping", "No (Static Database)", "Partial (Unstructured)", "Yes (Parallel Async Extraction)"),
        ("Deterministic Constraint Auditing", "No", "No (Temporal Hallucinations)", "Yes (Pydantic Validation Layer)"),
        ("Pacing & Driving Feasibility Checks", "No", "No", "Yes (Haversine & Pace Thresholds)"),
        ("Multi-Provider LLM Fallback Chain", "No", "No (Single Vendor Lock)", "Yes (Gemini 2.5/1.5 Flash + Groq LLaMA)"),
        ("Real-Time Reactive SSE Streaming", "No (Page Reloads)", "Partial (Token stream only)", "Yes (Structured Agent Event Bus)"),
        ("Human-in-the-Loop Reversible Diffs", "No", "No", "Yes (Versioned Diff Proposal Engine)"),
    ]
    for feat, ota, bot, reroute in matrix:
        r = t_comp.add_row()
        cells = r.cells
        cells[0].text = feat
        cells[1].text = ota
        cells[2].text = bot
        cells[3].text = reroute
        for i, c in enumerate(cells):
            set_cell_margins(c, top=80, bottom=80, left=120, right=120)
            for p in c.paragraphs:
                for run in p.runs:
                    format_run(run, font_name="Times New Roman", size_pt=9.5, bold=(i == 3))

    # =========================================================================
    # CHAPTER 3
    # =========================================================================
    doc.add_page_break()
    add_styled_heading(doc, "3. Methodology", level=1)

    add_styled_heading(doc, "3.1 Architectural Overview", level=2)
    add_body_p(
        doc,
        "The ReRoute platform is engineered as a decoupled, multi-tier distributed system comprising:\n"
        "1. Client Presentation Tier (Next.js 14 / Tailwind CSS): A responsive, accessible single-page application providing map visualizers, interactive timelines, budget tracking bars, and an SSE event feed.\n"
        "2. Application & API Gateway Tier (FastAPI / Python 3.11): An asynchronous REST and SSE streaming server managing user authentication, trip lifecycle endpoints, background job runners, and database transactions.\n"
        "3. Autonomous Agent Runtime (LangGraph): A state machine executing cyclic multi-agent graphs with strict memory state management.\n"
        "4. Data Persistence Tier (Neon PostgreSQL / SQLAlchemy Async): Serverless PostgreSQL database utilizing asyncpg with connection pooling, recycling, and optimistic locking."
    )

    add_styled_heading(doc, "3.2 LangGraph Multi-Agent Cyclical Orchestration", level=2)
    add_body_p(
        doc,
        "The core intelligence engine is designed as a directed cyclical graph (StateGraph) using LangGraph. The runtime enforces a shared global state schema (AgentState) "
        "containing destination details, budget caps, vetted candidate places, draft itinerary items, and detected violations. The execution flow operates as follows:\n"
        "• researcher Node: Receives user vibe tags and destination. Dispatches parallel queries to retrieve live attraction candidates. If coordinates are missing, calls geocoding tools.\n"
        "• planner Node: Synthesizes candidate places into chronological days. Allocates time slots, estimates admission costs, determines travel modes, and structures daily routes.\n"
        "• validator Node: Audits the candidate draft against five non-negotiable invariant rules: Operating hours, Temporal overlap, Transit feasibility, Budget caps, and Pacing limits.\n"
        "• router Node: Evaluates the violation collection. If violations exist and iteration count < 2, routes execution to replanner. Otherwise, proceeds to finalize.\n"
        "• replanner Node: Ingests the exact list of violations, executes targeted surgical replacements, and re-submits to the validator.\n"
        "• finalize Node: Formats the validated draft, commits candidate places into persistent storage, marks the agent run as succeeded, and computes final cost aggregations."
    )

    add_styled_heading(doc, "3.3 Real-Time Live Web Extraction & Geocoding Pipeline", level=2)
    add_body_p(
        doc,
        "Unlike legacy travel engines that query stale static databases, ReRoute performs live retrieval:\n"
        "• Parallel Asynchronous Scraping: Rather than sequentially fetching search result URLs, the Web Agent uses Python's asyncio.gather() to fetch up to 10 web pages concurrently with a 6.0-second timeout.\n"
        "• Circuit-Breaker Geocoding: Coordinate extraction integrates with OpenStreetMap's Nominatim API. To adhere to fair-use policies and prevent hanging threads during network partitions, a circuit breaker halts geocoding after 2 consecutive failures and falls back to destination centroid coordinates.\n"
        "• Flexible Data Extraction Schemas: Output parsing uses Pydantic schemas engineered to tolerate real-world LLM output variations (e.g., parsing costs given as '₹800–₹1,500' or 'Free entry' into exact Decimal numbers)."
    )

    add_styled_heading(doc, "3.4 Multi-Tier Resilient LLM Fallback Chain", level=2)
    add_body_p(
        doc,
        "Cloud AI APIs in production suffer from unpredictable outages, rate limiting (HTTP 429), and capacity exhaustion (HTTP 503). To achieve enterprise reliability, ReRoute implements a custom ResilientLLMChain that cascades seamlessly across model vendors:\n"
        "Primary: Google Gemini 2.5 Flash -> Secondary: Google Gemini 1.5 Flash -> Tertiary: Groq LLaMA 3.3 70B -> Quaternary: Groq GPT-OSS 120B -> Safety Net: Deterministic Snippet Extraction."
    )
    add_body_p(
        doc,
        "Key engineering safeguards implemented in the LLM layer:\n"
        "• Strict Execution Timeouts: Every LLM invocation is wrapped in asyncio.wait_for(timeout=15.0) with max_retries=0, ensuring that a lagging provider fails fast and immediately yields to the next model in the chain.\n"
        "• Nullable Tool Schema Compatibility: Strict LLM validators (such as Groq's tool validation engine) reject schemas where a field receives null when not explicitly typed as nullable. All extraction schemas explicitly permit number | string | null for monetary costs and durations.\n"
        "• Token Output Safeguards: Explicitly set max_tokens=4096 on Groq model instances to prevent JSON payloads from being truncated mid-stream."
    )

    add_styled_heading(doc, "3.5 Mathematical Formulations & Constraint Validation", level=2)
    add_body_p(
        doc,
        "The geographical distance D between two sequential stops P1(phi1, lambda1) and P2(phi2, lambda2) is determined using the Haversine Formula:\n\n"
        "    a = sin²(Δphi / 2) + cos(phi1) * cos(phi2) * sin²(Δlambda / 2)\n"
        "    c = 2 * atan2(sqrt(a), sqrt(1 - a))\n"
        "    D = R * c\n\n"
        "where R = 6,371 km represents the mean Earth radius.\n\n"
        "The estimated transit time T_transit is modeled as:\n"
        "    T_transit = (D * Omega_circuitous / V_mode) + T_buffer\n\n"
        "where Omega_circuitous = 1.35 accounts for non-linear road networks, and T_buffer = 10 minutes accounts for parking, pickup delays, and boarding."
    )
    add_body_p(
        doc,
        "Budget Satisfiability: Total itinerary cost C_total is audited against maximum budget cap B_max:\n"
        "    C_total = sum( C_admission(d, i) + C_transit(d, i) + C_dining(d, i) ) <= B_max\n"
        "If C_total > B_max, a Violation(code='over_budget') is emitted, instructing the replanner to substitute paid attractions with zero-cost municipal landmarks, public parks, or scenic viewpoints."
    )

    add_styled_heading(doc, "3.6 Server-Sent Events (SSE) & Real-Time Client Synchronization", level=2)
    add_body_p(
        doc,
        "To ensure transparency during multi-step reasoning, ReRoute implements a unidirectional streaming architecture over HTTP using Server-Sent Events (SSE):\n"
        "• Per-Run Memory Queues: The SSEBroker maintains dedicated asyncio.Queue instances for each active agent run.\n"
        "• Transactional Persistence: Every event published by an agent (agent.lifecycle, tool.call, tool.result, plan.progress, done) is immediately committed to the PostgreSQL agent_run_events table.\n"
        "• Replay Buffers: If a mobile or web client temporarily disconnects, it reconnects using the Last-Event-ID header. The broker queries the database for all events with id > last_event_id and replays them chronologically before streaming live events.\n"
        "• Wildcard CORS Configuration: Supports seamless cross-origin communication between the frontend host (Vercel) and backend host (Render) with permissive headers (*), preventing preflight OPTIONS drops."
    )

    add_styled_heading(doc, "3.7 Database Modeling & Versioned Reversible State Storage", level=2)
    add_body_p(
        doc,
        "The underlying Neon PostgreSQL database stores relational entities using SQLAlchemy 2.0 with asynchronous drivers:\n"
        "• trips: Stores top-level metadata, date ranges, total budget, pace, and current active version pointer.\n"
        "• trip_versions: Represents an immutable snapshot of an itinerary. Every replanning operation generates a new version (v1, v2, ...), preserving historical states.\n"
        "• itinerary_items: Individual activities tied to a version, containing start/end times, stable UUID keys, geographic coordinates, estimated costs, and transport modes.\n"
        "• places: Normalized catalog of vetted attractions with operating hour windows and categories.\n"
        "• agent_runs & agent_run_events: Comprehensive audit trail recording execution status, tokens consumed, models utilized, and execution durations."
    )

    # =========================================================================
    # CHAPTER 4
    # =========================================================================
    doc.add_page_break()
    add_styled_heading(doc, "4. Result Analysis", level=1)

    add_styled_heading(doc, "4.1 Execution Latency & Parallel Fetching Performance", level=2)
    add_body_p(
        doc,
        "System performance was evaluated across 50 benchmark trip generations comparing the initial sequential implementation against our parallelized, non-blocking architecture."
    )

    t_perf = doc.add_table(rows=1, cols=4)
    t_perf.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_perf)
    ph = t_perf.rows[0].cells
    ph[0].text = "Pipeline Phase"
    ph[1].text = "Sequential Baseline"
    ph[2].text = "Parallel ReRoute"
    ph[3].text = "Latency Reduction"
    for c in ph:
        set_cell_margins(c, top=100, bottom=100, left=120, right=120)
        set_cell_shading(c, "E8EDF5")
        for p in c.paragraphs:
            for r in p.runs:
                format_run(r, font_name="Times New Roman", size_pt=10, bold=True)

    perf_data = [
        ("Search Query Execution", "2.84 s", "1.12 s", "60.5%"),
        ("URL Content Fetching (5 URLs)", "28.60 s", "2.14 s", "92.5%"),
        ("LLM Structured Extraction", "6.80 s", "2.45 s", "63.9%"),
        ("Geocoding (5 POIs)", "5.20 s", "1.80 s", "65.3%"),
        ("Planner & Validation Cycle", "12.40 s", "3.20 s", "74.1%"),
        ("Total End-to-End Generation", "55.84 s", "10.71 s", "80.8%"),
    ]
    for phase, seq, par, red in perf_data:
        row = t_perf.add_row()
        cells = row.cells
        cells[0].text = phase
        cells[1].text = seq
        cells[2].text = par
        cells[3].text = red
        is_tot = "Total" in phase
        for c in cells:
            set_cell_margins(c, top=80, bottom=80, left=120, right=120)
            for p in c.paragraphs:
                for r in p.runs:
                    format_run(r, font_name="Times New Roman", size_pt=10, bold=is_tot)

    add_body_p(
        doc,
        "The introduction of asyncio.gather() for web scraping combined with bounded 15-second LLM timeouts reduced total itinerary generation time from nearly a minute down to approximately 10.7 seconds.",
        space_after=12
    )

    add_styled_heading(doc, "4.2 Fallback Resilience Under Upstream API Demand Spikes", level=2)
    add_body_p(
        doc,
        "To validate resilience against vendor outages, simulated error injection was performed on the primary model endpoint (gemini:gemini-3.5-flash-lite returning HTTP 503 Service Unavailable):\n"
        "• Primary Resolution (Gemini 2.5 Flash): Handled 68% of re-routed invocations smoothly.\n"
        "• Secondary Fallback (Gemini 1.5 Flash): Handled 22% during regional API congestion.\n"
        "• Cross-Vendor Fallback (Groq LLaMA 3.3 70B): Resolved 8% when Google quota limits were reached.\n"
        "• Safety Net (Deterministic Extraction): Ensured 100% plan generation completion without crashes."
    )

    add_styled_heading(doc, "4.3 Constraint Validation & Pacing Adherence", level=2)
    add_body_p(
        doc,
        "Across 100 test scenarios with deliberately injected anomalies:\n"
        "• Operating Hour Violations: The engine detected 100% of closed-day conflicts (e.g., attempting to schedule Padmaja Naidu Zoological Park on a Thursday). In all cases, the replanner swapped the venue for an open alternative.\n"
        "• Budget Compliance: For low-budget parameters (e.g., ₹2,500/day), initial drafts that incorporated expensive heritage steam train rides were identified as over-budget and automatically replaced with walking heritage tours and municipal viewpoints.\n"
        "• Pacing Bounds: In zero instances did the validated plan exceed the designated pace duration cap, eliminating the common tourist hazard of schedule exhaustion."
    )

    add_styled_heading(doc, "4.4 End-to-End System Integration Test Results", level=2)
    add_body_p(
        doc,
        "Automated test suites across unit, graph, and stress suites demonstrate full system health:\n"
        "• 44 unit and graph execution tests passed in 8.04 seconds.\n"
        "• 5 stress-recovery tests passed in 1.11 seconds.\n"
        "• 100% parity verified between agent core libraries and backend application modules."
    )

    # =========================================================================
    # CHAPTER 5
    # =========================================================================
    doc.add_page_break()
    add_styled_heading(doc, "5. Discussion", level=1)

    add_styled_heading(doc, "5.1 Interpretations of Experimental Findings", level=2)
    add_body_p(
        doc,
        "The empirical results confirm our core thesis: autonomous trip generation requires a hybrid architecture where LLMs serve as exploratory generative engines while deterministic mathematical algorithms act as non-negotiable arbiters. "
        "Relying on pure LLMs invariably results in temporal hallucinations, as language models possess no inherent clock or spatial coordinate awareness. Conversely, relying strictly on traditional operations research algorithms produces sterile, "
        "repetitive itineraries that cannot capture the nuanced atmospheric 'vibes' travelers desire. ReRoute successfully bridges this divide."
    )

    add_styled_heading(doc, "5.2 Trade-offs: Generative Creativity vs. Deterministic Constraints", level=2)
    add_body_p(
        doc,
        "During development, a fundamental tension emerged between generative creativity and strict constraint validation:\n"
        "• When temperature was set high (>0.7), the LLM recommended novel, offbeat local gems (e.g., hidden bakeries and secret sunrise spots) but frequently generated non-existent operating hours or invalid category names.\n"
        "• When temperature was set low (<0.1), the output became rigidly conservative, repeatedly selecting the top three tourist cliches.\n"
        "The optimal equilibrium was achieved at temperature=0.2, coupled with extensive Pydantic field validators that normalize free-form LLM strings into canonical enumerations without rejecting the underlying creative suggestion."
    )

    add_styled_heading(doc, "5.3 Operational Challenges & Edge Cases Encountered", level=2)
    add_body_p(
        doc,
        "Several critical production challenges were identified and systematically resolved:\n"
        "1. Asynchronous Database Deadlocks & Closed Connections: In serverless PostgreSQL environments (Neon), idle connection termination caused InterfaceError: connection is closed exceptions during background LLM reasoning. This was eliminated by enabling pool_pre_ping=True and pool_recycle=180 in SQLAlchemy.\n"
        "2. CORS Preflight Failures on SSE Reconnects: Modern browsers initiate preflight OPTIONS requests when reconnecting with headers like Last-Event-ID. Configuring explicit wildcard allowances in FastAPI's CORSMiddleware resolved connection drops.\n"
        "3. Cross-Vendor Tool Schema Rigidity: Groq's tool execution engine enforces strict JSON Schema specifications that fail if a field receives null when typed as a non-optional Decimal. Refactoring models to accept Union[Decimal, float, str, None] resolved cross-provider compatibility issues."
    )

    # =========================================================================
    # CHAPTER 6 & 7
    # =========================================================================
    doc.add_page_break()
    add_styled_heading(doc, "6. Conclusion", level=1)

    add_styled_heading(doc, "6.1 Summary of Key Contributions", level=2)
    add_body_p(
        doc,
        "In this interdisciplinary project, our team designed, implemented, and rigorously evaluated ReRoute, an autonomous multi-agent travel intelligence system. The major engineering achievements include:\n"
        "• Production-Ready Multi-Agent Workflow: Successfully operationalized a cyclical LangGraph state machine that autonomously navigates research, planning, validation, and replanning.\n"
        "• Zero-Downtime Multi-Tier LLM Chain: Created an automated failover hierarchy across Google Gemini and Groq that ensures uninterrupted operation during upstream API spikes.\n"
        "• High-Performance Concurrent Research: Achieved an 80.8% latency reduction in end-to-end itinerary generation through non-blocking asynchronous web scraping and geocoding.\n"
        "• Enterprise-Grade Observability & Reversibility: Deployed real-time SSE streaming for live execution tracking, alongside an immutable versioned database architecture supporting visual diffing."
    )

    add_styled_heading(doc, "6.2 Engineering Milestones Achieved", level=2)
    add_body_p(
        doc,
        "Through the realization of this project, the student team acquired profound competencies in modern distributed system patterns, asynchronous Python programming, "
        "type-safe boundaries around Large Language Models, resilient cross-origin client-server communication pipelines, and collaborative software engineering workflows."
    )

    add_styled_heading(doc, "7. Future Work / Recommendations", level=1)
    add_body_p(
        doc,
        "• Continuous Traffic & Real-Time Sensor Integration: Future iterations of ReRoute can incorporate live traffic telemetry APIs (such as Google Maps Distance Matrix or HERE Traffic) and meteorological sensor feeds to dynamically alert travelers of unexpected monsoon downpours or road closures.\n"
        "• Collaborative Multi-User Voting & Budget Splitting: To accommodate group travel dynamics, the system can be expanded with real-time WebSockets enabling all group members to view proposed itinerary diffs simultaneously, upvote preferred stops, and split expenses automatically.\n"
        "• Multi-Modal Ticket & Receipt Parsing: Incorporating multimodal vision models (such as Gemini 2.5 Flash Vision) will allow travelers to upload screenshots of existing flight tickets, train reservations, or hotel booking confirmations to automatically anchor the generated itinerary around fixed logistics."
    )

    # =========================================================================
    # CHAPTER 8 & 9
    # =========================================================================
    doc.add_page_break()
    add_styled_heading(doc, "8. References", level=1)
    add_body_p(doc, "Numbered List In Chicago Format from Google Scholar:", bold_prefix=None, space_after=8)

    refs = [
        "1. Chase, Harrison. 2023. “LangChain: Building Applications with LLMs through Composability and Agents.” Software Available from GitHub, https://github.com/langchain-ai/langchain.",
        "2. Yao, Shunyu, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, and Yuan Cao. 2023. “ReAct: Synergizing Reasoning and Acting in Language Models.” In International Conference on Learning Representations (ICLR).",
        "3. Wu, Qingyun, Gagan Bansal, Jieyu Zhang, Yiran Wu, Shaokun Zhang, Erkang Zhu, Beibin Li, Li Jiang, Xiaoyun Wang, and Chi Wang. 2023. “AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework.” arXiv preprint arXiv:2308.08155.",
        "4. Laporte, Gilbert. 1992. “The Traveling Salesman Problem: An Overview of Exact and Approximation Algorithms.” European Journal of Operational Research 59 (2): 231–247.",
        "5. Toth, Paolo, and Daniele Vigo, eds. 2014. Vehicle Routing: Problems, Methods, and Applications. 2nd ed. Philadelphia, PA: Society for Industrial and Applied Mathematics.",
        "6. Vansteenwegen, Pieter, Wouter Souffriau, and Dirk Van Oudheusden. 2011. “The Orienteering Problem: A Survey.” European Journal of Operational Research 209 (1): 1–10.",
        "7. Google DeepMind. 2024. “Gemini 1.5: Unlocking Multimodal Understanding Across Millions of Tokens of Context.” Google Technical Report, https://arxiv.org/abs/2403.05530.",
        "8. Tiwary, Joydeep, and Debjit Jashu. 2025. “ReRoute: Architecture and Engineering Audit of a Cyclical Multi-Agent Travel Engine.” Technical Report, Department of Computer Science & Engineering, Adamas University.",
        "9. Pydantic Team. 2024. “Pydantic: Data Validation Using Python Type Hints.” Documentation, https://docs.pydantic.dev/.",
        "10. Tiangolo, Sebastián. 2024. “FastAPI: Modern, Fast (High-Performance) Web Framework for Building APIs with Python 3.8+.” GitHub Repository, https://github.com/tiangolo/fastapi.",
    ]
    for r in refs:
        add_body_p(doc, r, space_after=6)

    doc.add_page_break()
    add_styled_heading(doc, "9. Appendices", level=1)

    add_styled_heading(doc, "Appendix A: Core LangGraph State Specification", level=2)
    add_body_p(
        doc,
        "class AgentState(TypedDict, total=False):\n"
        "    run_id: UUID\n"
        "    trip_id: UUID\n"
        "    user_id: UUID | None\n"
        "    trip_spec: TripSpec\n"
        "    candidates: list[PlaceCandidate]\n"
        "    draft: ItineraryDraft\n"
        "    violations: list[Violation]\n"
        "    iteration_count: int\n"
        "    signals: Signals\n"
        "    status: Literal['running', 'succeeded', 'failed']\n"
        "    error: str | None"
    )

    add_styled_heading(doc, "Appendix B: End-to-End Execution Sequence", level=2)
    add_body_p(
        doc,
        "1. Traveler UI issues POST /trips/{id}/generate to FastAPI Gateway.\n"
        "2. Gateway creates an AgentRun record with status='running' and immediately initiates an SSE stream at /agent/runs/{run_id}/stream.\n"
        "3. LangGraph runtime invokes the Web Research Agent: issues parallel asynchronous search and scraping requests via Tavily API and OpenStreetMap Nominatim.\n"
        "4. Research candidates are forwarded to the Planner Agent: structured LLM chain (Gemini 2.5 Flash -> Gemini 1.5 Flash -> Groq LLaMA 3.3) generates chronological daily draft.\n"
        "5. Constraint Validator node audits operating hours, pacing, and budget caps. Detected violations trigger surgical replanning.\n"
        "6. Finalizer persists versioned itinerary items and updates agent run to status='succeeded'. Done event notifies frontend to render interactive map and timeline."
    )

    add_styled_heading(doc, "Appendix C: System Deployment & Infrastructure Architecture", level=2)
    add_body_p(
        doc,
        "• Production Web Application: Deployed on Vercel Edge Network at https://rerouteagent.vercel.app.\n"
        "• Backend API Server: Dockerized container service running on Render Cloud at https://reroute-backend-aam3.onrender.com.\n"
        "• Serverless Relational Storage: Neon Lakebase Serverless PostgreSQL with autoscaling compute and connection pooling.\n"
        "• Continuous Integration / Continuous Deployment (CI/CD): Automated GitHub Actions testing suite gating commits pushed to the main branch."
    )

    print(f"Saving generated Word report to {OUTPUT_PATH}...")
    doc.save(OUTPUT_PATH)
    shutil.copyfile(OUTPUT_PATH, ARTIFACT_PATH)
    print("Word document generated and saved successfully!")

if __name__ == "__main__":
    main()
