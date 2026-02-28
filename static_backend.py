from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from groq_key_manager import GroqKeyManager, AllKeysExhaustedError


load_dotenv()

class CodeReviewState(TypedDict):
    code: str
    
    style_report: Optional[str]
    type_report: Optional[str]
    security_report: Optional[str]
    complexity_report: Optional[str]
    documentation_report: Optional[str]
    
    final_report: Optional[str]
    fixed_code: Optional[str]



# Shared key manager — handles automatic rotation on rate-limit errors
key_manager = GroqKeyManager(
    model="openai/gpt-oss-20b",
    temperature=0,
    max_retries_per_key=1,
    cooldown_seconds=5.0,
)



############################## FUNCTIONS ############################################################

def style_linting_agent(state: CodeReviewState):
    prompt = f"""
You are a professional static code style analyzer.

Perform style linting on this Python/SQL code:
- PEP8 compliance
- Naming conventions
- Formatting
- Indentation
- Readability issues

Code:
{state['code']}
"""

    content = key_manager.invoke(prompt)
    return {"style_report": content}




def type_checking_agent(state: CodeReviewState):
    prompt = f"""
Perform static type analysis:

Check:
- Type mismatches
- Missing type hints (Python)
- SQL datatype problems
- Logical type inconsistencies

Code:
{state['code']}
"""

    content = key_manager.invoke(prompt)
    return {"type_report": content}





def security_agent(state: CodeReviewState):
    prompt = f"""
Perform static security analysis.

Check for:
- SQL Injection
- Hardcoded credentials
- Unsafe eval/exec
- Input validation issues
- Deserialization risks
- Injection vulnerabilities

Code:
{state['code']}
"""

    content = key_manager.invoke(prompt)
    return {"security_report": content}




def complexity_agent(state: CodeReviewState):
    prompt = f"""
Analyze code complexity.

Check:
- Cyclomatic complexity
- Deep nesting
- Long functions
- Duplicate logic
- Maintainability issues

Code:
{state['code']}
"""

    content = key_manager.invoke(prompt)
    return {"complexity_report": content}




def documentation_agent(state: CodeReviewState):
    prompt = f"""
Review documentation quality:

Check:
- Missing docstrings
- Missing comments
- Poor function explanations
- API documentation gaps

Code:
{state['code']}
"""

    content = key_manager.invoke(prompt)
    return {"documentation_report": content}




def report_agent(state: CodeReviewState):
    prompt = f"""
Create a professional structured code audit report.

STYLE ANALYSIS:
{state['style_report']}

TYPE ANALYSIS:
{state['type_report']}

SECURITY ANALYSIS:
{state['security_report']}

COMPLEXITY ANALYSIS:
{state['complexity_report']}

Generate:
1. Executive Summary
2. Detailed Findings
3. Risk Severity (Low/Medium/High)
4. Actionable Recommendations
"""

    content = key_manager.invoke(prompt)
    return {"final_report": content}




def code_fixer_agent(state: CodeReviewState):
    prompt = f"""
You are a senior software engineer.

Fix the following code based on the audit report.

ORIGINAL CODE:
{state['code']}

AUDIT REPORT:
{state['final_report']}

Return ONLY the improved corrected code.
"""

    content = key_manager.invoke(prompt)
    return {"fixed_code": content}











workflow = StateGraph(CodeReviewState)

# Add Nodes
workflow.add_node("style", style_linting_agent)
workflow.add_node("type", type_checking_agent)
workflow.add_node("security", security_agent)
workflow.add_node("complexity", complexity_agent)
workflow.add_node("documentation", documentation_agent)
workflow.add_node("report", report_agent)
workflow.add_node("fixer", code_fixer_agent)



# Sequential flow (safe execution)
workflow.add_edge(START, "style")
workflow.add_edge(START, "type")
workflow.add_edge(START, "security")
workflow.add_edge(START, "complexity")
workflow.add_edge(START, "documentation")

workflow.add_edge("style", "report")
workflow.add_edge("type", "report")
workflow.add_edge("security", "report")
workflow.add_edge("complexity", "report")
workflow.add_edge("documentation", "report")

workflow.add_edge("report", "fixer")
workflow.add_edge("fixer", END)

app = workflow.compile()


