from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class InvestmentReport(BaseModel):
    """Structured investment research report — Modules 6 & 7."""
    company_name: str = Field(description="The exact company or ticker being analyzed.")
    industry: str = Field(description="The industry or sector the company operates in.")
    company_overview: str = Field(description="A concise overview of the company's business.")
    business_model: str = Field(description="How the company generates revenue.")
    latest_news: str = Field(description="Summary of the most recent relevant news or announcements.")
    strengths: List[str] = Field(description="3-5 key strengths of the company.")
    weaknesses: List[str] = Field(description="3-5 key weaknesses or challenges.")
    financial_highlights: str = Field(description="Notable financial figures, revenue growth, or earnings data.")
    growth_opportunities: List[str] = Field(description="2-4 potential growth opportunities.")
    potential_risks: List[str] = Field(description="2-4 potential risks to the investment thesis.")
    investment_summary: str = Field(description="A final investment recommendation summary, 2-4 sentences.")
    executive_summary: Optional[str] = Field(default="", description="High-level executive brief suitable for C-level or clients.")
    conclusion: Optional[str] = Field(default="", description="Concluding strategic assessment.")
    references: Optional[List[str]] = Field(default_factory=list, description="List of source references and disclosures.")


class CompanyComparison(BaseModel):
    """Structured output for multi-company comparisons — Module 5."""
    companies_compared: List[str] = Field(description="Names of companies compared.")
    comparison_summary: str = Field(description="A narrative summary comparing the companies.")
    recommended_pick: str = Field(description="Which company looks strongest and why, in one sentence.")
    strengths_by_company: Optional[Dict[str, List[str]]] = Field(default_factory=dict, description="Key strengths per company.")
    key_takeaways: Optional[List[str]] = Field(default_factory=list, description="3-5 key takeaways from the comparison.")


class EmailDraft(BaseModel):
    """Email draft model for client/manager communication — Module 11."""
    recipient: str = Field(default="manager@company.com", description="Target recipient email.")
    subject: str = Field(description="Subject line of the email.")
    body: str = Field(description="Professional body of the investment email.")


class FinancialCalculation(BaseModel):
    """Financial computation result — Module 10."""
    calculation_type: str = Field(description="CAGR, ROI, Growth Percentage, or Custom Formula.")
    result_text: str = Field(description="Formatted calculation output.")
    explanation: str = Field(description="Brief explanation of the calculation formula and financial interpretation.")
