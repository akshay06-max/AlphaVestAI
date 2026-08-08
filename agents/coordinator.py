"""
Coordinator layer — Modules 5, 6, 7, 8, 10, 11.

- Module 5: RunnableParallel multi-company comparison
- Module 6: Pydantic structured investment report
- Module 7: Sequential pipeline (Research -> Read PDF -> Merge -> Analyze -> Generate Report -> Executive Summary -> Email Draft)
- Module 8: RunnableBranch conditional routing
- Module 10: Financial calculation execution
- Module 11: Email draft generation and dispatch
"""
import re
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnableBranch
from langchain_core.output_parsers import PydanticOutputParser

from config import llm
from agents.research_agent import research_company
from tools.search_tools import news_tool
from tools.financial_tools import run_financial_calculation_query, financial_tools
from tools.email_tools import generate_email_draft, send_email_via_smtp
from models.schemas import InvestmentReport, CompanyComparison, EmailDraft


def _get_structured_output(schema_cls, prompt_text: str):
    """Invoke structured output with graceful fallback to Pydantic JSON parser if tool_choice fails."""
    try:
        structured_llm = llm.with_structured_output(schema_cls)
        return structured_llm.invoke(prompt_text)
    except Exception:
        parser = PydanticOutputParser(pydantic_object=schema_cls)
        full_prompt = (
            f"{prompt_text}\n\n"
            f"IMPORTANT: Return ONLY valid JSON matching this schema:\n"
            f"{parser.get_format_instructions()}\n"
            f"Do not include Markdown backticks (```json) or conversational text."
        )
        response = llm.invoke(full_prompt)
        text = response.content if hasattr(response, "content") else str(response)
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            return parser.parse(text)
        except Exception:
            return schema_cls.model_validate_json(text)


# ---------- Module 5: Parallel multi-company research ----------

def extract_companies(query: str) -> list[str]:
    """Extract list of companies from comparative user queries."""
    cleaned = re.sub(r"(?i)\b(compare|versus|vs\.?|research|and|between)\b", ",", query)
    parts = re.split(r"[,&]", cleaned)
    companies = [p.strip().strip(".?!") for p in parts if len(p.strip()) > 1]
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for c in companies:
        if c.lower() not in seen and c.lower() not in ["the", "all", "these", "companies", "products"]:
            seen.add(c.lower())
            deduped.append(c)
    return deduped


def build_parallel_chain(companies: list[str]):
    branches = {c: RunnableLambda(lambda x, c=c: research_company(f"Research {c}")) for c in companies}
    return RunnableParallel(branches)


def compare_companies(query: str) -> dict:
    """Module 5: Parallel research execution and comparative synthesis."""
    companies = extract_companies(query)
    if len(companies) < 2:
        companies = ["Microsoft", "Google", "Amazon"]  # default robust multi-company fallback
    
    chain = build_parallel_chain(companies)
    results = chain.invoke({})
    combined_text = "\n\n".join(f"### {c}\n{txt}" for c, txt in results.items())
    
    comparison = _get_structured_output(
        CompanyComparison,
        f"Compare these companies based on the research below:\n{combined_text}"
    )
    return {"raw_research": results, "comparison": comparison}


# ---------- Module 6 & 7: Sequential pipeline -> structured report -> executive summary -> email draft ----------

def _step_research(inputs: dict) -> dict:
    return {**inputs, "research": research_company(inputs["query"])}


def _step_read_pdf(inputs: dict, retriever=None) -> dict:
    pdf_context = ""
    if retriever is not None:
        try:
            docs = retriever.invoke(inputs["query"])
            pdf_context = "\n".join(d.page_content for d in docs)
        except Exception:
            pdf_context = ""
    return {**inputs, "pdf_context": pdf_context}


def _step_merge(inputs: dict) -> dict:
    combined = (
        f"Web/Wikipedia Research Context:\n{inputs.get('research', '')}\n\n"
        f"Uploaded Financial/Annual Report Context:\n{inputs.get('pdf_context', '(no specific uploaded PDF excerpts)')}"
    )
    return {**inputs, "combined": combined}


def _step_analyze(inputs: dict) -> dict:
    prompt = (
        f"Analyze this research for company analysis:\n{inputs['combined']}\n\n"
        f"Extract key quantitative metrics, business health, competitive positioning, and risks."
    )
    analysis = llm.invoke(prompt)
    analysis_text = analysis.content if hasattr(analysis, "content") else str(analysis)
    return {**inputs, "analysis": analysis_text}


def _step_generate_report(inputs: dict) -> dict:
    report = _get_structured_output(
        InvestmentReport,
        f"Generate a complete structured investment research report for the query '{inputs['query']}' "
        f"using this research and analysis:\n\n{inputs['combined']}\n\nKey Analysis:\n{inputs.get('analysis', '')}"
    )
    return {**inputs, "report": report}


def _step_executive_summary(inputs: dict) -> dict:
    report = inputs.get("report")
    company_name = report.company_name if report else inputs["query"]
    prompt = (
        f"Write a high-impact, C-level executive summary for {company_name} based on the investment report:\n"
        f"{report.investment_summary if report else inputs.get('analysis', '')}"
    )
    res = llm.invoke(prompt)
    exec_summary = res.content if hasattr(res, "content") else str(res)
    if report:
        report.executive_summary = exec_summary.strip()
    return {**inputs, "executive_summary": exec_summary}


def _step_email_draft(inputs: dict, client_name: str = "Client", client_email: str = None) -> dict:
    report = inputs.get("report")
    summary_for_email = (
        f"Company: {report.company_name if report else inputs['query']}\n"
        f"Investment Thesis: {report.investment_summary if report else ''}\n"
        f"Executive Summary: {inputs.get('executive_summary', '')}\n"
        f"Key Strengths: {', '.join(report.strengths) if report else ''}\n"
        f"Risks: {', '.join(report.potential_risks) if report else ''}"
    )
    email_draft = generate_email_draft(
        summary_for_email,
        client_name=client_name,
        client_email=client_email,
    )
    return {**inputs, "email_draft": email_draft}


def run_sequential_pipeline(query: str, retriever=None, client_name: str = "Client", client_email: str = None) -> dict:
    """Module 7: Research -> Read PDF -> Merge -> Analyze -> Generate Report -> Executive Summary -> Email Draft."""
    pipeline = (
        RunnableLambda(_step_research)
        | RunnableLambda(lambda x: _step_read_pdf(x, retriever))
        | RunnableLambda(_step_merge)
        | RunnableLambda(_step_analyze)
        | RunnableLambda(_step_generate_report)
        | RunnableLambda(_step_executive_summary)
        | RunnableLambda(lambda x: _step_email_draft(x, client_name, client_email))
    )
    result = pipeline.invoke({"query": query})
    return {
        "report": result["report"],
        "executive_summary": result.get("executive_summary", ""),
        "email_draft": result.get("email_draft"),
        "pdf_context": result.get("pdf_context", ""),
        "raw_research": result.get("research", ""),
    }


# ---------- Module 8: Conditional routing (RunnableBranch) ----------

def _is_comparison(inputs: dict) -> bool:
    q = inputs["query"].lower()
    return ("compare" in q or " vs " in q or " versus " in q) and len(extract_companies(inputs["query"])) >= 2


def _is_calculation(inputs: dict) -> bool:
    q = inputs["query"].lower()
    return any(k in q for k in ["cagr", "roi", "growth percentage", "annual growth", "calculate", "comparison table", "table of"])


def _is_pdf_question(inputs: dict) -> bool:
    q = inputs["query"].lower()
    return any(k in q for k in ["annual report", "risk factor", "risk factors", "uploaded", "quarterly report", "future plans", "revenue growth in the report", "pdf"])


def _is_news_question(inputs: dict) -> bool:
    q = inputs["query"].lower()
    return any(k in q for k in ["news", "latest", "today", "stock price", "stock", "earnings", "results", "quarterly results", "market", "semiconductor"])


def _is_email_request(inputs: dict) -> bool:
    q = inputs["query"].lower()
    return any(k in q for k in ["email", "send report", "send email", "draft email", "mail to"])


def route_query(query: str, retriever=None, client_name: str = "Client", client_email: str = None) -> dict:
    """Module 8: Router deciding which agent handles the request."""
    inputs = {"query": query}

    router = RunnableBranch(
        (_is_email_request, RunnableLambda(lambda x: {
            "type": "email",
            "result": generate_email_draft(x["query"], client_name=client_name, client_email=client_email)
        })),
        (_is_comparison, RunnableLambda(lambda x: {
            "type": "comparison",
            "result": compare_companies(x["query"])
        })),
        (_is_calculation, RunnableLambda(lambda x: {
            "type": "calculation",
            "result": run_financial_calculation_query(x["query"])
        })),
        (_is_pdf_question, RunnableLambda(lambda x: {
            "type": "pdf",
            "result": run_sequential_pipeline(x["query"], retriever, client_name=client_name, client_email=client_email)
        })),
        (_is_news_question, RunnableLambda(lambda x: {
            "type": "news",
            "result": news_tool.run(x["query"])
        })),
        # Default: Full Sequential Investment Pipeline
        RunnableLambda(lambda x: {
            "type": "general_research",
            "result": run_sequential_pipeline(x["query"], retriever, client_name=client_name, client_email=client_email)
        }),
    )
    return router.invoke(inputs)
