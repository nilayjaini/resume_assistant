import streamlit as st
import openai
from docx import Document
import tempfile
import os
import base64
from io import BytesIO

# === CONFIG ===
openai.api_key = st.secrets.get("OPENAI_API_KEY", "sk-...")

# === AGENT 1: GitHub Summary Agent (placeholder logic) ===
def extract_github_summary(github_url):
    # TODO: You can enhance this with GitHub API or repo scraping logic
    return f"Simulated GitHub summary for {github_url}"

# === AGENT 2: LLM Generator ===
def generate_project_summary(subject, description, repo_summary):
    prompt = f"""
    Subject: {subject}
    Description: {description}
    GitHub Content: {repo_summary}

    Generate a resume project title and 3-4 bullet points.
    Format it like:
    Title line with project and dates
    • Bullet 1
    • Bullet 2
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a resume assistant that writes clean project summaries."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# === AGENT 3: Resume Editor Agent ===
def update_resume(docx_file, project_block):
    doc = Document(docx_file)
    inserted = False

    for i, para in enumerate(doc.paragraphs):
        if "PROJECT EXPERIENCE" in para.text.upper():
            insertion_point = i + 1
            doc.paragraphs[insertion_point].insert_paragraph_before(project_block)
            inserted = True
            break

    if not inserted:
        doc.add_paragraph("\nPROJECT EXPERIENCE")
        doc.add_paragraph(project_block)

    tmp_path = tempfile.mktemp(suffix=".docx")
    doc.save(tmp_path)
    return tmp_path

# === AGENT 4: Resume Feedback Agent ===
def get_resume_feedback(docx_file):
    text = "\n".join([p.text for p in Document(docx_file).paragraphs])
    prompt = f"""
    You are a professional resume coach.
    Please analyze the following resume content:

    {text}

    Give:
    1. 3–5 improvement suggestions
    2. Any weak or redundant phrases
    3. Tips for tailoring it to job descriptions
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# === STREAMLIT UI ===
st.set_page_config(page_title="AI Resume Assistant", layout="centered")
st.title("📄 AI Resume Editor + Feedback Tool")

with st.sidebar:
    subject = st.text_input("Project Subject")
    description = st.text_area("Project Description")
    github_url = st.text_input("GitHub Repo URL (optional)")
    uploaded_resume = st.file_uploader("Upload Resume (.docx)", type="docx")

if uploaded_resume and subject and description:
    with st.spinner("Running multi-agent pipeline..."):
        repo_summary = extract_github_summary(github_url)
        project_block = generate_project_summary(subject, description, repo_summary)
        updated_path = update_resume(uploaded_resume, project_block)
        feedback = get_resume_feedback(updated_path)

    st.success("✅ Resume Updated")

    with open(updated_path, "rb") as f:
        st.download_button("📥 Download Updated Resume", f, file_name="Updated_Resume.docx")

    st.subheader("🧠 Resume Feedback")
    st.markdown(feedback)
else:
    st.info("👈 Fill out all inputs to generate your AI-enhanced resume.")

