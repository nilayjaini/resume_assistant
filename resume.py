import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from openai import OpenAI
import anthropic
import io

# === API Clients ===
client_openai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
client_claude = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# === GPT-4 Bullet Point Generator ===
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
    return response.choices[0].message.content.strip()

# === Replace First Project (Surgically and Neatly) ===
def replace_first_project_safely(doc, new_title, new_bullets, new_date="Jan 2024 – May 2024"):
    bullet_points = [bp.strip() for bp in new_bullets.strip().split("•") if bp.strip()]
    section_found = False
    replaced = False
    i = 0

    while i < len(doc.paragraphs):
        para = doc.paragraphs[i]

        if "PROJECT EXPERIENCE" in para.text.strip().upper():
            section_found = True
            i += 1
            continue

        # Find the first project under Project Experience
        if section_found and para.text.strip().isupper() and not replaced:
            # Replace the title
            para.text = f"{new_title}        {new_date}"
            para.style = 'Normal'
            if para.runs:
                para.runs[0].font.bold = True
                para.runs[0].font.size = Pt(11)

            # Delete old bullets until next all-caps heading
            j = i + 1
            while j < len(doc.paragraphs):
                if doc.paragraphs[j].text.strip().isupper():
                    break
                del doc.paragraphs[j]

            # Insert new bullets at correct index
            insert_index = i + 1
            for bullet in bullet_points:
                new_para = doc.add_paragraph()
                run = new_para.add_run(f"• {bullet}")
                run.font.size = Pt(10.5)
                new_para.paragraph_format.left_indent = Inches(0.25)
                doc.paragraphs.insert(insert_index, new_para)
                insert_index += 1

            replaced = True
            break

        i += 1

    return doc

# === Resume Text Extractor for Claude Feedback ===
def extract_text_from_docx(docx_file):
    doc = Document(docx_file)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])

# === Claude Feedback Agent ===
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

# === STREAMLIT APP UI ===
st.set_page_config(page_title="Agentic Resume Assistant", layout="centered")
st.title("🤖 Agentic AI Resume Assistant")
st.markdown("Upload your resume, replace 1 project, and get GPT & Claude feedback!")

uploaded_file = st.file_uploader("📄 Upload your `.docx` resume", type=["docx"])

if uploaded_file:
    st.success("✅ Resume uploaded successfully!")

    st.subheader("🛠️ Replace First Project")
    subject = st.text_input("Project Title", placeholder="e.g., Business Analytics Toolbox")
    description = st.text_area("Project Description", height=150)
    github_url = st.text_input("GitHub Repository URL (optional)")
    date_range = st.text_input("Project Date Range", value="Jan 2024 – May 2024")

    if st.button("✨ Update Resume & Get Feedback"):
        with st.spinner("Generating bullet points using GPT-4..."):
            bullet_points = generate_bullet_points(subject, description, github_url)

        with st.spinner("Replacing the first project in your resume..."):
            doc = Document(uploaded_file)
            updated_doc = replace_first_project_safely(doc, subject.upper(), bullet_points, date_range)
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
