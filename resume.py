import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
import openai
import anthropic
import os
import io

# ========== CONFIG ==========
openai.api_key = os.getenv("OPENAI_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=anthropic_api_key)

# ========== GPT: Bullet Point Generator ==========
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
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content.strip()

# ========== DOCX: Replace First Project ==========
def replace_first_project_safely(doc, new_title, new_bullets):
    bullet_points = new_bullets.strip().split("•")
    bullet_points = [bp.strip() for bp in bullet_points if bp.strip()]
    replaced = False

    for i, para in enumerate(doc.paragraphs):
        if para.text.strip().isupper() and not replaced:
            para.text = new_title
            para.style.font.size = Pt(11)
            para.style.font.bold = True

            # Delete old bullets
            j = i + 1
            while j < len(doc.paragraphs) and doc.paragraphs[j].text.strip().startswith("•"):
                doc.paragraphs[j].clear()
                j += 1

            # Add new bullets
            for bullet in bullet_points:
                bullet_para = doc.add_paragraph(style='List Bullet')
                run = bullet_para.add_run(f"• {bullet}")
                run.font.size = Pt(10.5)
                bullet_para.paragraph_format.left_indent = Inches(0.25)

            replaced = True
            break

    return doc

# ========== CLAUDE: Feedback Generator ==========
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
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        system=system_prompt,
        max_tokens=1000,
        temperature=0.4,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response.content[0].text

# ========== DOCX: Extract Resume Text ==========
def extract_text_from_docx(docx_file):
    doc = Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])

# ========== STREAMLIT APP ==========
st.set_page_config(page_title="Agentic Resume Assistant", layout="centered")
st.title("🤖 Agentic AI Resume Assistant")
st.markdown("Upload your resume, add a project, and get feedback — powered by GPT-4 and Claude 3.5.")

# Upload Resume
uploaded_file = st.file_uploader("📄 Upload your `.docx` resume", type=["docx"])

if uploaded_file:
    st.success("Resume uploaded successfully!")

    # Project Input
    st.subheader("🛠️ Add New Project")
    subject = st.text_input("Subject Name")
    description = st.text_area("Project Description")
    github_url = st.text_input("GitHub Repository URL")

    if st.button("✨ Generate Resume & Feedback"):
        with st.spinner("Generating bullet points using GPT..."):
            bullet_points = generate_bullet_points(subject, description, github_url)

        with st.spinner("Updating resume with new project..."):
            doc = Document(uploaded_file)
            updated_doc = replace_first_project_safely(doc, subject.upper(), bullet_points)

            # Save in memory
            output_buffer = io.BytesIO()
            updated_doc.save(output_buffer)
            output_buffer.seek(0)

            updated_text = extract_text_from_docx(output_buffer)

        with st.spinner("🔍 Getting feedback from Claude..."):
            feedback = get_resume_feedback_from_claude(updated_text)

        st.subheader("✅ Updated Resume Preview")
        st.text_area("Resume Content", updated_text, height=300)

        st.download_button(
            label="📥 Download Updated Resume",
            data=output_buffer,
            file_name="Updated_Resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        st.subheader("💬 Claude's Resume Feedback")
        st.markdown(feedback)
