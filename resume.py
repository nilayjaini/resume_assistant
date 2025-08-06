import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from openai import OpenAI
import anthropic
import io

# === API Clients ===
client_openai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
client_claude = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# === GPT Bullet Point Generator ===
def generate_bullet_points(subject, description, github_url):
    prompt = f"""You are a resume expert. Based on the project below, generate 2–3 strong, concise resume bullet points:

Subject: {subject}
Description: {description}
GitHub: {github_url}

Format:
• [bullet 1]
• [bullet 2]
(only 2–3 total)
"""
    response = client_openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content.strip().split("•")

# === Your Exact Colab-Style Replacement Function ===
def replace_first_project_safely(doc, new_title, new_bullets):
    def delete_paragraph(paragraph):
        p = paragraph._element
        p.getparent().remove(p)
        p._p = p._element = None

    def format_bullet(paragraph, text):
        run = paragraph.add_run(f"• {text}")
        run.font.size = Pt(10.5)
        paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        paragraph.paragraph_format.left_indent = Inches(0.25)
        paragraph.paragraph_format.first_line_indent = Inches(-0.15)
        paragraph.paragraph_format.space_after = Pt(0)

    def format_title(paragraph, text):
        run = paragraph.add_run(text)
        run.bold = True
        run.font.size = Pt(12)
        paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    section_found = False
    start_idx = -1
    end_idx = -1

    for i, para in enumerate(doc.paragraphs):
        if "PROJECT EXPERIENCE" in para.text.upper():
            section_found = True
            continue
        if section_found and start_idx == -1 and para.text.strip():
            start_idx = i
            continue
        if section_found and start_idx != -1:
            if para.runs and para.runs[0].bold:
                end_idx = i
                break
    if end_idx == -1:
        for j in range(start_idx + 1, len(doc.paragraphs)):
            if doc.paragraphs[j].text.strip() == "":
                end_idx = j
                break
        else:
            end_idx = len(doc.paragraphs)

    for idx in reversed(range(start_idx, end_idx)):
        delete_paragraph(doc.paragraphs[idx])

    insert_idx = start_idx
    for bullet in reversed(new_bullets):
        bullet_para = doc.paragraphs[insert_idx].insert_paragraph_before("")
        format_bullet(bullet_para, bullet)

    title_para = doc.paragraphs[insert_idx].insert_paragraph_before("")
    format_title(title_para, new_title)

    return doc

# === Extract DOCX Text for Feedback ===
def extract_text_from_docx(docx_file):
    doc = Document(docx_file)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])

# === Claude Feedback ===
def get_resume_feedback_from_claude(resume_text):
    system_prompt = "You're a career coach reviewing resumes for clarity, impact, and relevance."
    user_prompt = f"""Evaluate the following resume:

{resume_text}

Give me:
1. 3–5 specific improvement suggestions
2. Weak or vague bullet points, if any
3. Suggestions for tailoring to roles like: data analyst, product manager, ML engineer.
Return your response in a clear bullet list.
"""
    response = client_claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        system=system_prompt,
        max_tokens=1000,
        temperature=0.4,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response.content[0].text

# === STREAMLIT UI ===
st.set_page_config(page_title="Agentic Resume Assistant", layout="centered")
st.title("🤖 Agentic AI Resume Assistant")
st.markdown("Upload your resume, replace the first project (perfect formatting), and get GPT + Claude feedback.")

uploaded_file = st.file_uploader("📄 Upload your `.docx` resume", type=["docx"])

if uploaded_file:
    st.success("✅ Resume uploaded successfully!")

    st.subheader("🛠️ Replace First Project")
    subject = st.text_input("Project Title", placeholder="Business Analytics Toolbox – Trends and Transitions in Men's College Basketball        Jan 2024 – May 2024")
    description = st.text_area("Project Description", height=150)
    github_url = st.text_input("GitHub Repository URL (optional)")

    if st.button("✨ Update Resume & Get Feedback"):
        with st.spinner("Generating bullet points using GPT-4..."):
            bullet_points = generate_bullet_points(subject, description, github_url)

        with st.spinner("Replacing the first project in your resume..."):
            doc = Document(uploaded_file)
            updated_doc = replace_first_project_safely(doc, subject.upper(), bullet_points)
            buffer = io.BytesIO()
            updated_doc.save(buffer)
            buffer.seek(0)
            resume_text = extract_text_from_docx(buffer)

        with st.spinner("Getting feedback from Claude..."):
            feedback = get_resume_feedback_from_claude(resume_text)

        st.subheader("✅ Updated Resume Preview")
        st.text_area("Resume Text", resume_text, height=300)

        st.download_button(
            label="📥 Download Updated Resume",
            data=buffer,
            file_name="Updated_Resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        st.subheader("💬 Claude's Feedback")
        st.markdown(feedback)
