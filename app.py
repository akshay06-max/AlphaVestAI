"""
AlphaVest Capital — AI Investment & Financial Research Assistant
Full implementation of Capstone Project 3 (Pages 15-20 of Handbook).
"""
import os
import uuid
import streamlit as st
import pandas as pd

from config import llm, MODEL_NAME
from rag.loader import load_and_split
from rag.vectorstore import build_vectorstore, get_retriever
from memory.db import (
    init_db,
    save_message,
    load_history,
    list_sessions,
    save_preference,
    get_preference,
    add_researched_company,
    save_report_archive,
    list_archived_reports,
    get_archived_report,
)
from agents.coordinator import route_query, compare_companies, run_sequential_pipeline
from tools.financial_tools import run_financial_calculation_query, calculate_cagr, calculate_roi, calculate_growth_percentage
from tools.email_tools import generate_email_draft, send_email_via_smtp
from tools.pdf_generator import generate_investment_report_pdf, generate_comparison_pdf
from models.schemas import InvestmentReport, CompanyComparison, EmailDraft

# ---------------- Streamlit App Configuration ----------------
st.set_page_config(
    page_title="AlphaVest AI — Investment & Financial Research",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Storage & SQLite Memory
os.makedirs("data/uploads", exist_ok=True)
conn = init_db()

# Session State Setup
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "messages" not in st.session_state:
    st.session_state.messages = []
if "retriever" not in st.session_state:
    st.session_state.retriever = None
if "client_name" not in st.session_state:
    st.session_state.client_name = "AlphaVest Client"
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "last_comparison" not in st.session_state:
    st.session_state.last_comparison = None

# ---------------- Sidebar Requirements (Handbook Page 18) ----------------
with st.sidebar:
    st.markdown("## 💹 **AlphaVest Capital**")
    st.caption("AI Investment Advisory & Financial Research")
    st.divider()

    # 0. AI Provider & Key Settings (for Streamlit Cloud & local)
    with st.expander("🔑 **AI Provider & API Key**", expanded=not bool(os.getenv("GROQ_API_KEY") or os.getenv("OPENROUTER_API_KEY"))):
        curr_groq = os.getenv("GROQ_API_KEY", "")
        masked_groq = (curr_groq[:7] + "..." + curr_groq[-4:]) if len(curr_groq) > 12 else ""
        st.caption(f"Active Provider: **{'Groq (Llama 3.3 70B)' if curr_groq else 'OpenRouter / Default'}**")
        input_groq = st.text_input("Groq API Key (100% Free - 14.4k req/day)", value=curr_groq, type="password", placeholder="gsk_...", help="Get a free key instantly at https://console.groq.com/keys")
        if st.button("💾 Save & Activate API Key"):
            if input_groq.strip():
                os.environ["GROQ_API_KEY"] = input_groq.strip()
                os.environ["GROQ_MODEL"] = "llama-3.3-70b-versatile"
                st.success("✅ Groq Llama 3.3 70B activated successfully!")
                st.rerun()

    # 1. Investor Profile & Long-Term Memory (Module 9)
    with st.expander("👤 **Investor Profile & Memory**", expanded=False):
        try:
            prof_row = get_preference(conn, st.session_state.client_name)
        except Exception:
            prof_row = None
        saved_risk = prof_row[1] if prof_row and prof_row[1] else "Growth / Moderate"
        saved_ind = prof_row[2] if prof_row and prof_row[2] else "Technology, AI, Semiconductors, Clean Energy"
        saved_freq = prof_row[3] if prof_row and prof_row[3] else "None yet"
        saved_interests = prof_row[4] if prof_row and prof_row[4] else "Long-term compounding, high-margin SaaS"
        saved_style = prof_row[5] if prof_row and prof_row[5] else "Comprehensive Analyst Deep Dive"
        saved_email = prof_row[6] if prof_row and prof_row[6] else "manager@company.com"

        c_name = st.text_input("Client / Investor Name", value=st.session_state.client_name, key="prof_name")
        c_email = st.text_input("Client Email Address", value=saved_email, key="prof_email")
        c_risk = st.selectbox(
            "Risk Profile",
            ["Conservative / Capital Preservation", "Growth / Moderate", "Aggressive / High Growth"],
            index=["Conservative / Capital Preservation", "Growth / Moderate", "Aggressive / High Growth"].index(saved_risk) if saved_risk in ["Conservative / Capital Preservation", "Growth / Moderate", "Aggressive / High Growth"] else 1,
        )
        c_style = st.selectbox(
            "Preferred Report Style",
            ["Comprehensive Analyst Deep Dive", "Executive C-Level Summary", "Quantitative Financial Brief"],
            index=["Comprehensive Analyst Deep Dive", "Executive C-Level Summary", "Quantitative Financial Brief"].index(saved_style) if saved_style in ["Comprehensive Analyst Deep Dive", "Executive C-Level Summary", "Quantitative Financial Brief"] else 0,
        )
        c_ind = st.text_area("Preferred Industries / Interests", value=saved_ind)

        if st.button("💾 Save Profile Preferences"):
            st.session_state.client_name = c_name
            save_preference(
                conn,
                client_name=c_name,
                risk_profile=c_risk,
                preferred_industries=c_ind,
                investment_interests=saved_interests,
                preferred_report_style=c_style,
                client_email=c_email,
            )
            st.success("Investor profile preferences saved to SQLite memory!")

        st.caption(f"**Frequently Researched:** {saved_freq}")

    # 2. Email & Gmail SMTP Dispatch Settings (Module 11)
    with st.expander("✉️ **Email & Gmail SMTP Dispatch**", expanded=False):
        st.caption("Configure Gmail credentials to send live emails to your inbox.")
        smtp_sender = st.text_input("Your Gmail Address (Sender)", value=os.getenv("EMAIL_SENDER", ""), key="smtp_user", placeholder="your.email@gmail.com")
        smtp_pass = st.text_input("Google App Password (16-chars)", value=os.getenv("EMAIL_PASSWORD", ""), key="smtp_pass", type="password", help="Generate at https://myaccount.google.com/apppasswords")
        if st.button("💾 Save Email Credentials"):
            os.environ["EMAIL_SENDER"] = smtp_sender.strip()
            os.environ["EMAIL_PASSWORD"] = smtp_pass.strip()
            st.session_state.smtp_sender = smtp_sender.strip()
            st.session_state.smtp_pass = smtp_pass.strip()
            st.success("✅ Gmail SMTP credentials saved for this session!")

    st.divider()

    # 2. Document Uploads (Annual Reports & Quarterly Reports - Module 4)
    st.subheader("📄 **Upload Financial Reports (RAG)**")
    doc_type = st.radio("Document Category:", ["Annual Report (10-K)", "Quarterly Report (10-Q)", "Investor Presentation", "Financial Statement"], horizontal=False)
    uploaded_files = st.file_uploader("Upload PDF / TXT / CSV", type=["pdf", "txt", "csv"], accept_multiple_files=True)

    if uploaded_files and st.button("⚡ Build Knowledge Base (ChromaDB)"):
        total_chunks = []
        with st.spinner("Processing documents & building Chroma embeddings..."):
            for up_file in uploaded_files:
                path = os.path.join("data/uploads", up_file.name)
                with open(path, "wb") as f:
                    f.write(up_file.getbuffer())
                chunks = load_and_split(path, doc_type=doc_type)
                total_chunks.extend(chunks)
            if total_chunks:
                vectorstore = build_vectorstore(total_chunks)
                st.session_state.retriever = get_retriever(vectorstore)
                st.success(f"✅ Indexed {len(total_chunks)} chunks across {len(uploaded_files)} file(s) into ChromaDB!")

    # 3. View Uploaded Reports
    with st.expander("📁 **Uploaded Document Repository**", expanded=False):
        uploaded_list = os.listdir("data/uploads")
        if uploaded_list:
            for f in uploaded_list:
                size_kb = os.path.getsize(os.path.join("data/uploads", f)) / 1024
                st.caption(f"• `{f}` ({size_kb:.1f} KB)")
        else:
            st.caption("No files uploaded yet. Upload an annual or quarterly report above.")

    st.divider()

    # 4. Previous Conversations & History (Module 9)
    st.subheader("🕘 **Conversation History**")
    sessions = list_sessions(conn)
    if sessions:
        picked = st.selectbox("Switch Session:", ["(Current Session)"] + sessions)
        if picked != "(Current Session)" and st.button("📂 Load Selected Session"):
            history = load_history(conn, picked)
            st.session_state.messages = [{"role": r, "content": c} for r, c, _ in history]
            st.session_state.session_id = picked
            st.rerun()

    if st.button("🗑️ Clear Current Chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # 5. Archived Reports (Module 12)
    with st.expander("📚 **Archived Reports (Module 12)**", expanded=False):
        try:
            archived = list_archived_reports(conn, st.session_state.client_name)
        except Exception:
            archived = []
        if archived:
            for rep_id, comp_name, r_type, s_text, dt in archived[:5]:
                st.markdown(f"**{comp_name}** ({r_type}) — *{dt}*")
                st.caption(s_text[:120] + "...")
        else:
            st.caption("Generated reports will automatically be archived here.")


# ---------------- Main Screen (Handbook Page 18) ----------------
st.markdown("## 💹 **AI Investment & Financial Research Assistant**")
st.caption(
    f"Active Client: **`{st.session_state.client_name}`** | Session: **`{st.session_state.session_id}`** | LLM: **`{MODEL_NAME}`**"
)

# Illustrative Prompt Quick Shortcuts (Handbook Page 16, 17, 18)
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    if st.button("🏢 Research NVIDIA"):
        st.session_state.messages.append({"role": "user", "content": "Research NVIDIA and summarize business overview, revenue sources, and competitors."})
        st.rerun()
with col2:
    if st.button("⚖️ Compare Mega-Caps"):
        st.session_state.messages.append({"role": "user", "content": "Compare Microsoft, Google, Amazon, and Meta."})
        st.rerun()
with col3:
    if st.button("📊 Calculate CAGR"):
        st.session_state.messages.append({"role": "user", "content": "Calculate CAGR for a company that grew from 100 to 250 over 5 years."})
        st.rerun()
with col4:
    if st.button("📄 Risk Factors in PDF"):
        st.session_state.messages.append({"role": "user", "content": "Summarize the risk factors and future plans from the uploaded annual report."})
        st.rerun()
with col5:
    if st.button("📧 Email Client Brief"):
        st.session_state.messages.append({"role": "user", "content": "Email today's investment report to the client."})
        st.rerun()

st.divider()

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input Box
user_input = st.chat_input("Ask about a company, request comparison, calculate CAGR/ROI, or say 'Remember that I prefer...'")

if user_input:
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    save_message(conn, st.session_state.session_id, "user", user_input)

    # 2. Module 9 — Long-Term Memory Keyword Trigger
    if "remember that" in user_input.lower():
        preference_snippet = user_input.replace("remember that", "").replace("Remember that", "").strip()
        save_preference(conn, st.session_state.client_name, preferred_industries=preference_snippet)
        reply = f"🧠 **Got it!** I've updated your investor profile and remembered your preference: *'{preference_snippet}'*."
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        save_message(conn, st.session_state.session_id, "assistant", reply)

    # 3. Main Agent Routing & Execution (Modules 2-8, 10, 11)
    else:
        try:
            with st.spinner("🔍 AlphaVest agents executing multi-source financial research..."):
                outcome = route_query(
                    user_input,
                    retriever=st.session_state.retriever,
                    client_name=st.session_state.client_name,
                    client_email=c_email,
                )

            result_type = outcome.get("type", "general_research")
            result = outcome.get("result", "")

            with st.chat_message("assistant"):
                # ---------------- Case A: Multi-Company Comparison (Module 5) ----------------
                if result_type == "comparison":
                    comparison: CompanyComparison = result["comparison"]
                    raw_data = result.get("raw_research", {})
                    st.session_state.last_comparison = comparison

                    st.markdown(f"### ⚖️ Multi-Company Comparative Analysis: {', '.join(comparison.companies_compared)}")
                    st.markdown(f"**Recommended Pick:** 🏆 **{comparison.recommended_pick}**")
                    st.markdown(comparison.comparison_summary)

                    # Comparison Summary Expander
                    with st.expander("📊 **Comparative Highlights & Company Research**", expanded=True):
                        cols = st.columns(len(comparison.companies_compared))
                        for idx, comp in enumerate(comparison.companies_compared):
                            with cols[idx]:
                                st.markdown(f"#### **{comp}**")
                                txt = raw_data.get(comp, "Research completed.")
                                st.write(txt[:500] + ("..." if len(txt) > 500 else ""))
                                add_researched_company(conn, st.session_state.client_name, comp)

                    # Download Buttons (TXT + PDF)
                    c_txt_data = f"ALPHAVEST COMPARATIVE ANALYSIS: {', '.join(comparison.companies_compared)}\n\nRECOMMENDED PICK:\n{comparison.recommended_pick}\n\nSUMMARY:\n{comparison.comparison_summary}\n"
                    pdf_bytes = generate_comparison_pdf(comparison, raw_data)

                    dcol1, dcol2 = st.columns(2)
                    with dcol1:
                        st.download_button("⬇️ Download Comparison (TXT)", data=c_txt_data, file_name="comparison_report.txt", mime="text/plain")
                    with dcol2:
                        st.download_button("⬇️ Download Comparison (PDF)", data=pdf_bytes, file_name="comparison_report.pdf", mime="application/pdf")

                    save_report_archive(conn, st.session_state.client_name, ", ".join(comparison.companies_compared), "Comparison", {}, comparison.comparison_summary)
                    reply_text = f"**Comparative Analysis for {', '.join(comparison.companies_compared)}**\n\n**Recommendation:** {comparison.recommended_pick}\n\n{comparison.comparison_summary}"

                # ---------------- Case B: Structured Investment Report / Sequential Pipeline (Modules 6 & 7) ----------------
                elif result_type in ("general_research", "pdf"):
                    if isinstance(result, dict) and "report" in result:
                        report: InvestmentReport = result["report"]
                        exec_summary = result.get("executive_summary", "")
                        email_draft: EmailDraft = result.get("email_draft")
                        pdf_ctx = result.get("pdf_context", "")
                        st.session_state.last_report = report

                        st.markdown(f"### 🏢 Investment Research Report: **{report.company_name}**")
                        st.markdown(f"**Sector / Industry:** *{report.industry}*")
                        st.markdown(f"**Investment Recommendation:** {report.investment_summary}")

                        # Expandable Sections (Handbook Page 18)
                        with st.expander("💼 **Company Overview & Business Model**", expanded=False):
                            st.markdown(f"**Overview:** {report.company_overview}")
                            st.markdown(f"**Business Model & Revenue Generation:** {report.business_model}")

                        with st.expander("📈 **Financial Highlights & Latest News**", expanded=False):
                            st.markdown(f"**Financial Highlights:** {report.financial_highlights}")
                            st.markdown(f"**Recent News & Announcements:** {report.latest_news}")

                        with st.expander("⚖️ **Strategic SWOT Analysis (Strengths & Risks)**", expanded=True):
                            scol1, scol2 = st.columns(2)
                            with scol1:
                                st.markdown("##### **✅ Key Strengths**")
                                for s in report.strengths:
                                    st.markdown(f"- {s}")
                                st.markdown("##### **🚀 Growth Opportunities**")
                                for g in report.growth_opportunities:
                                    st.markdown(f"- {g}")
                            with scol2:
                                st.markdown("##### **⚠️ Potential Risks & Challenges**")
                                for r in report.potential_risks:
                                    st.markdown(f"- {r}")
                                st.markdown("##### **⚠️ Weaknesses**")
                                for w in report.weaknesses:
                                    st.markdown(f"- {w}")

                        if exec_summary:
                            with st.expander("🎯 **Executive Summary & Final Recommendation**", expanded=False):
                                st.markdown(exec_summary)

                        if pdf_ctx:
                            with st.expander("📄 **Retrieved Annual Report / PDF Excerpts**", expanded=False):
                                st.markdown(pdf_ctx[:1000] + ("..." if len(pdf_ctx) > 1000 else ""))

                        # Email Integration preview & send (Module 11)
                        if email_draft:
                            with st.expander("✉️ **Generated Client Email Draft (Module 11)**", expanded=False):
                                target_to = st.text_input("Send To Email:", value=email_draft.recipient, key=f"to_{uuid.uuid4().hex[:4]}")
                                st.markdown(f"**Subject:** `{email_draft.subject}`")
                                st.text_area("Email Body", value=email_draft.body, height=140, key=f"email_{uuid.uuid4().hex[:4]}")
                                if st.button("🚀 Send Email to Client via Gmail SMTP", key=f"btn_{uuid.uuid4().hex[:4]}"):
                                    send_res = send_email_via_smtp(
                                        target_to,
                                        email_draft.subject,
                                        email_draft.body,
                                        sender_email=os.environ.get("EMAIL_SENDER"),
                                        sender_password=os.environ.get("EMAIL_PASSWORD"),
                                    )
                                    if send_res["status"] == "sent":
                                        st.success(send_res["message"])
                                    elif send_res["status"] == "error":
                                        st.error(send_res["message"])
                                    else:
                                        st.info(send_res["message"])

                        # Download Options (TXT + PDF - Handbook Page 18)
                        full_report_text = (
                            f"ALPHAVEST CAPITAL INVESTMENT REPORT: {report.company_name}\n"
                            f"Industry: {report.industry}\n\n"
                            f"EXECUTIVE SUMMARY:\n{exec_summary if exec_summary else report.investment_summary}\n\n"
                            f"OVERVIEW:\n{report.company_overview}\n\n"
                            f"BUSINESS MODEL:\n{report.business_model}\n\n"
                            f"FINANCIAL HIGHLIGHTS:\n{report.financial_highlights}\n\n"
                            f"LATEST NEWS:\n{report.latest_news}\n\n"
                            f"STRENGTHS:\n" + "\n".join(f"- {s}" for s in report.strengths) + "\n\n"
                            f"WEAKNESSES:\n" + "\n".join(f"- {w}" for w in report.weaknesses) + "\n\n"
                            f"GROWTH OPPORTUNITIES:\n" + "\n".join(f"- {g}" for g in report.growth_opportunities) + "\n\n"
                            f"POTENTIAL RISKS:\n" + "\n".join(f"- {r}" for r in report.potential_risks) + "\n\n"
                            f"INVESTMENT SUMMARY:\n{report.investment_summary}\n"
                        )
                        pdf_data = generate_investment_report_pdf(report)

                        dcol1, dcol2 = st.columns(2)
                        with dcol1:
                            st.download_button("⬇️ Download Report (TXT)", data=full_report_text, file_name=f"{report.company_name}_investment_report.txt", mime="text/plain")
                        with dcol2:
                            st.download_button("⬇️ Download Report (PDF)", data=pdf_data, file_name=f"{report.company_name}_investment_report.pdf", mime="application/pdf")

                        add_researched_company(conn, st.session_state.client_name, report.company_name)
                        save_report_archive(conn, st.session_state.client_name, report.company_name, "Full Investment Report", report.model_dump(), report.investment_summary)
                        reply_text = report.investment_summary
                    else:
                        reply_text = str(result)
                        st.markdown(reply_text)

                # ---------------- Case C: Financial Calculations / Python Tool (Module 10) ----------------
                elif result_type == "calculation":
                    reply_text = str(result)
                    st.markdown("### 📊 **Financial Calculation & Analytics**")
                    st.markdown(reply_text)
                    with st.expander("🔢 **Calculation Methodology & Python Formula**", expanded=False):
                        st.caption("Calculated using standard financial compound return and valuation algorithms in Python.")

                # ---------------- Case D: Financial News Agent (Module 2) ----------------
                elif result_type == "news":
                    reply_text = str(result)
                    st.markdown("### 📰 **Financial News & Market Intelligence**")
                    st.markdown(reply_text)
                    with st.expander("🔎 **Raw Internet Search Sources**", expanded=False):
                        st.write(reply_text)

                # ---------------- Case E: Email Agent (Module 11) ----------------
                elif result_type == "email":
                    if isinstance(result, EmailDraft):
                        draft: EmailDraft = result
                        st.markdown(f"### ✉️ **Investment Email Dispatch**")
                        target_recipient = st.text_input("Recipient Email:", value=draft.recipient, key="standalone_email_to")
                        st.markdown(f"**Subject:** `{draft.subject}`")
                        st.text_area("Email Content", value=draft.body, height=180, key="standalone_email_body")
                        if st.button("🚀 Send Email to Recipient via Gmail SMTP", key="standalone_send_btn"):
                            send_res = send_email_via_smtp(
                                target_recipient,
                                draft.subject,
                                draft.body,
                                sender_email=os.environ.get("EMAIL_SENDER"),
                                sender_password=os.environ.get("EMAIL_PASSWORD"),
                            )
                            if send_res["status"] == "sent":
                                st.success(send_res["message"])
                            elif send_res["status"] == "error":
                                st.error(send_res["message"])
                            else:
                                st.info(send_res["message"])

                        st.download_button("⬇️ Download Email Draft (.txt)", data=f"To: {target_recipient}\nSubject: {draft.subject}\n\n{draft.body}", file_name="email_draft.txt")
                        reply_text = f"Email draft prepared for **{target_recipient}** with subject *'{draft.subject}'*."
                    else:
                        reply_text = str(result)
                        st.markdown(reply_text)

                # Fallback display
                else:
                    reply_text = str(result)
                    st.markdown(reply_text)

            st.session_state.messages.append({"role": "assistant", "content": reply_text})
            save_message(conn, st.session_state.session_id, "assistant", reply_text)

        except Exception as e:
            error_msg = f"⚠️ An error occurred while processing your request: {e}\n\nPlease check your internet connection or model selection in `.env`."
            with st.chat_message("assistant"):
                st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            save_message(conn, st.session_state.session_id, "assistant", error_msg)
