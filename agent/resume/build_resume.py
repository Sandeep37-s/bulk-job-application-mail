"""Builds Sandeep_Kumar_Resume.pdf from RESUME below.

Edit the data, then run:  python agent/resume/build_resume.py
"""
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).with_name("Sandeep_Kumar_Resume.pdf")
LINK = HexColor("#1a0dab")

RESUME = {
    "name": "SANDEEP KUMAR",
    "contact": [
        ("+91-6005362383", None),
        ("sandeep22112002@gmail.com", "mailto:sandeep22112002@gmail.com"),
        ("LinkedIn", "https://www.linkedin.com/in/"),  # TODO: put your full LinkedIn URL
        ("GitHub", "https://github.com/Sandeep37-s"),
    ],
    "summary": (
        "AI Engineer and B.Tech Computer Science and Engineering graduate with hands-on experience in Machine "
        "Learning (ML), Deep Learning, Data Science, and Generative AI (GenAI). Skilled in building end-to-end "
        "Artificial Intelligence (AI) pipelines, including data preprocessing, feature engineering, model training, "
        "and deployment. Experienced in Natural Language Processing (NLP) and Retrieval-Augmented Generation (RAG) "
        "using LangChain and Large Language Models (LLMs)."
    ),
    "education": {
        "degree": "Bachelor of Technology", "dates": "Sep 2022 – Jul 2026",
        "field": "Computer Science and Engineering", "score": "CGPA: 7.5 / 10",
        "school": "Central University of Jammu, J&amp;K",
    },
    "experience": [
        {
            # Current job. TODO: confirm title, start month and bullets.
            "role": "AI Engineer", "org": "Dhruva Technology", "dates": "Jul 2026 – Present",
            "bullets": [
                "Building <b>LLM</b>-powered and <b>RAG</b>-based applications for production use cases.",
                "Developing <b>Generative AI</b> pipelines with Python, LangChain and FastAPI, from prototyping to deployment.",
            ],
        },
        {
            "role": "AI Intern", "org": "National Informatics Center (NIC)", "dates": "Jan 2026 – Jun 2026",
            "bullets": [
                "Engineered a <b>RAG</b>-based document intelligence system using LangChain, ChromaDB, and FastAPI.",
                "Developed an <b>LLM</b>-powered land information chatbot with semantic search and vector embeddings.",
                "Built end-to-end <b>Generative AI</b> pipelines for document processing, retrieval, and Question Answering.",
            ],
        },
        {
            "role": "Machine Learning Intern", "org": "Vaishnav Technologies", "dates": "Jun 2025 – Dec 2025",
            "bullets": [
                "Developed <b>Machine Learning (ML)</b> models using <b>Python</b>, Scikit-learn, Pandas, and NumPy.",
                "Applied data preprocessing, feature engineering, and model evaluation techniques.",
                "Built end-to-end ML pipelines for classification, prediction, and deployment.",
            ],
        },
        {
            "role": "GenAI Intern", "org": "Innomatics Research Labs", "dates": "Jan 2025 – Jul 2025",
            "bullets": [
                "Developed <b>LLM</b>-based applications with prompt engineering and GenAI workflows.",
                "Designed and optimized prompts for improved reasoning and context handling.",
                "Built end-to-end <b>GenAI</b> pipelines for intelligent AI applications.",
            ],
        },
    ],
    "projects": [
        {
            "name": "AyuScan – AI Health Analyzer",
            "bullets": [
                "Developed a <b>Computer Vision</b>-based system to detect visible health indicators from facial images.",
                "Applied OpenCV and HSV color analysis techniques for feature extraction.",
                "Deployed an end-to-end Flask web application for image processing and result visualization.",
            ],
        },
        {
            "name": "WildGuard AI – Anonymous Wildlife Crime Reporting System",
            "bullets": [
                "Built an AI-powered Telegram bot for automated wildlife crime classification.",
                "Implemented secure MySQL-based storage with real-time admin alerting.",
                "Designed a privacy-first architecture enabling fully anonymous reporting.",
            ],
        },
        {
            "name": "Financial Deep Research Agent",
            "bullets": [
                "Built a <b>multi-agent GenAI system</b> for financial research using query planning and sector-based routing.",
                "Integrated <b>RAG (ChromaDB)</b>, web search, and financial APIs for company and market analysis.",
                "Implemented <b>Python</b> financial metrics and deployed via <b>LangGraph/CrewAI + FastAPI</b>.",
            ],
        },
    ],
    "skills": [
        ("Programming Languages", "Python, C, C++, Java, SQL"),
        ("Artificial Intelligence (AI) / Machine Learning (ML)",
         "Deep Learning, Natural Language Processing (NLP), Computer Vision, Fine-Tuning, Prompt Engineering"),
        ("Tools/Technologies", "Linux, Git/GitHub, MySQL, XAMPP, Docker, Jupyter Notebook, Power BI"),
        ("Libraries/Frameworks",
         "Manim, TensorFlow, PyTorch, Scikit-learn, NLTK, OpenCV, Flask, FastAPI, LangChain, RAG, MCP"),
    ],
}

S = {
    "name": ParagraphStyle("name", fontName="Times-Bold", fontSize=20, leading=24, alignment=TA_CENTER),
    "contact": ParagraphStyle("contact", fontName="Times-Roman", fontSize=9.5, leading=12, alignment=TA_CENTER),
    "h": ParagraphStyle("h", fontName="Times-Bold", fontSize=12.5, leading=15, spaceBefore=6),
    "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=10, leading=12.4),
    "bold": ParagraphStyle("bold", fontName="Times-Bold", fontSize=10, leading=12.4),
    "right": ParagraphStyle("right", fontName="Times-Italic", fontSize=10, leading=12.4, alignment=2),
    "rightplain": ParagraphStyle("rightplain", fontName="Times-Roman", fontSize=10, leading=12.4, alignment=2),
    "bullet": ParagraphStyle("bullet", fontName="Times-Roman", fontSize=10, leading=12.4, leftIndent=10),
    "sub": ParagraphStyle("sub", fontName="Times-Roman", fontSize=10, leading=12.4, leftIndent=22, firstLineIndent=-8),
}


def heading(title):
    return [Paragraph(title, S["h"]), HRFlowable(width="100%", thickness=0.6, color="black", spaceBefore=1, spaceAfter=3)]


def row(left, right, lstyle="bold", rstyle="right"):
    t = Table([[Paragraph(left, S[lstyle]), Paragraph(right, S[rstyle])]], colWidths=["72%", "28%"])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


def build():
    r = RESUME
    contact = "&nbsp;&nbsp;&nbsp;&nbsp;".join(
        f'<link href="{url}"><font color="#1a0dab">{text}</font></link>' if url else text for text, url in r["contact"]
    )
    story = [Paragraph(r["name"], S["name"]), Paragraph(contact, S["contact"])]

    story += heading("P<font size=10>ROFESSIONAL</font> S<font size=10>UMMARY</font>")
    story.append(Paragraph(r["summary"], S["body"]))

    e = r["education"]
    story += heading("E<font size=10>DUCATION</font>")
    story += [row(e["degree"], f"({e['dates']})", rstyle="rightplain"),
              row(e["field"], e["score"], "body", "rightplain"),
              Paragraph(e["school"], S["body"])]

    story += heading("E<font size=10>XPERIENCE</font>/I<font size=10>NTERNSHIP</font>")
    for job in r["experience"]:
        story.append(row(f"•&nbsp;&nbsp;{job['role']} – {job['org']}", f"({job['dates']})"))
        story += [Paragraph(f"–&nbsp;&nbsp;{b}", S["sub"]) for b in job["bullets"]]
        story.append(Spacer(1, 2))

    story += heading("P<font size=10>ROJECTS</font>")
    for p in r["projects"]:
        story.append(Paragraph(f"•&nbsp;&nbsp;{p['name']}", S["bold"]))
        story += [Paragraph(f"–&nbsp;&nbsp;{b}", S["sub"]) for b in p["bullets"]]
        story.append(Spacer(1, 2))

    story += heading("S<font size=10>KILLS</font>")
    story += [Paragraph(f"•&nbsp;&nbsp;<b>{k}</b>: {v}", S["bullet"]) for k, v in r["skills"]]

    SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                      topMargin=10 * mm, bottomMargin=10 * mm, title="Sandeep Kumar – Resume",
                      author="Sandeep Kumar").build(story)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
