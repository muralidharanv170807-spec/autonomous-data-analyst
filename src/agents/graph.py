import json
import re
from typing import TypedDict, List, Dict, Any, Optional
import plotly.express as px
import pandas as pd
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from src.database.duckdb_engine import DuckDBEngine
from src.rag.vector_store import PolicyVectorStore


class AgentState(TypedDict):
    question: str
    route: str
    sql_query: str
    sql_results: List[Dict[str, Any]]
    sql_error: str
    sql_attempts: int
    sql_summary: str
    chart_json: Optional[Dict[str, Any]]
    rag_context: str
    citations: List[Dict[str, Any]]
    rag_summary: str
    policy_rules: List[str]
    answer: str
    groundedness_score: int
    eval_attempts: int


llm = ChatOllama(
    model="qwen3.5:9b",
    base_url="http://localhost:11434",
    num_ctx=16384,
    temperature=0,
    reasoning=False,
)
db_engine = DuckDBEngine(csv_directory="data")
vector_store = PolicyVectorStore(persist_path="./chroma_db")
if vector_store.get_collection_count() == 0:
    vector_store.add_files(["data/company_compliance_policy.pdf"])


def router_node(state: AgentState) -> Dict[str, Any]:
    prompt = (
        "Classify the user question into exactly one label: SQL_ANALYTICS, POLICY_RAG, or HYBRID.\n"
        "- SQL_ANALYTICS: numbers, totals, averages, counts, rankings, or trends from tables.\n"
        "- POLICY_RAG: rules, limits, caps, guidelines, or text definitions from policy documents.\n"
        "- HYBRID: checking table records against policy rules, thresholds, or compliance violations.\n"
        f"Question: {state['question']}\nReturn ONLY the label."
    )
    res = llm.invoke(prompt).content.strip().upper()
    for label in ("HYBRID", "SQL_ANALYTICS", "POLICY_RAG"):
        if label in res:
            return {"route": label}
    return {"route": "HYBRID"}


def policy_rag_node(state: AgentState) -> Dict[str, Any]:
    chunks = vector_store.query(state["question"], k=4)
    context_text = "\n\n".join(
        f"[{c.get('source', 'doc')} p.{c.get('page', '?')}]: {c.get('text', c.get('content', ''))}"
        for c in chunks
    )
    if state["route"] == "HYBRID":
        extract_prompt = (
            f"Extract the individual policy rules relevant to: {state['question']}\n"
            f"Policy Excerpts:\n{context_text}\n\n"
            "Return ONLY a valid JSON list of strings, where each string is ONE single self-contained rule "
            "with its exact scope (department, region, category) and threshold.\n"
            'Example: ["Employees with rating below 4.5 cannot receive a bonus above 9000", "Employees in Sales department cannot receive a bonus above 15000"]\n'
            "Do NOT include unrelated policies. Do NOT comment on missing records."
        )
        raw_rules = re.sub(r"```(?:json)?|```", "", llm.invoke(extract_prompt).content).strip()
        try:
            rules = json.loads(raw_rules)
            if not isinstance(rules, list) or not rules:
                rules = [raw_rules]
        except Exception:
            rules = [line.strip("-• ") for line in raw_rules.splitlines() if line.strip()]

        summary = "\n".join(f"- {r}" for r in rules)
        return {
            "rag_context": context_text,
            "citations": chunks,
            "rag_summary": summary,
            "policy_rules": rules,
        }

    prompt = (
        f"Answer the question strictly using the policy excerpts below: {state['question']}\n"
        f"Policy Excerpts:\n{context_text}\n"
        "Cite source and page numbers clearly."
    )
    summary = llm.invoke(prompt).content.strip()
    return {"rag_context": context_text, "citations": chunks, "rag_summary": summary, "policy_rules": []}


def _run_single_sql(question: str, schema: str, single_rule: str = "") -> tuple[str, List[Dict[str, Any]], str]:
    attempts = 0
    last_error = ""
    rule_block = ""
    if single_rule:
        rule_block = (
            f"\nSingle Policy Rule to Check:\n{single_rule}\n"
            "Write a DuckDB SELECT query returning all columns for rows that VIOLATE this single rule. "
            "Include every scope filter mentioned in the rule (e.g., department = 'Sales').\n"
        )

    while attempts < 3:
        attempts += 1
        err_hint = f"\nPrevious SQL failed with error: {last_error}. Fix it." if last_error else ""
        prompt = (
            f"Write a single DuckDB read-only SELECT SQL query for:\n{question}\n"
            f"Use ONLY the exact table and column names shown in the Schema below.\nSchema: {schema}"
            f"{rule_block}{err_hint}\n"
            "Return ONLY raw SQL without markdown fences."
        )
        sql = re.sub(r"```(?:sql)?|```", "", llm.invoke(prompt).content).strip()
        try:
            res_data = db_engine.execute_query(sql)
            rows = res_data.get("data", []) if isinstance(res_data, dict) else (res_data or [])
            return sql, rows, ""
        except Exception as e:
            last_error = str(e)
    return "", [], last_error


def sql_analyst_node(state: AgentState) -> Dict[str, Any]:
    schema = db_engine.get_schema()
    rules = state.get("policy_rules") or []

    if state["route"] == "HYBRID" and rules:
        all_queries: List[str] = []
        merged_rows: List[Dict[str, Any]] = []
        seen_keys = set()
        last_error = ""

        for rule in rules:
            sql, rows, err = _run_single_sql(state["question"], schema, single_rule=rule)
            if err:
                last_error = err
            if sql:
                all_queries.append(f"-- Rule: {rule}\n{sql}")
            for row in rows:
                row_key = json.dumps(row, sort_keys=True, default=str)
                if row_key not in seen_keys:
                    seen_keys.add(row_key)
                    merged_rows.append(row)

        combined_sql = "\n\n".join(all_queries)
        chart_json = None
        if merged_rows and len(merged_rows) > 1 and len(merged_rows[0]) >= 2:
            df = pd.DataFrame(merged_rows)
            cols = list(df.columns)
            fig = px.bar(df, x=cols[0], y=cols[1], title=state["question"][:60])
            chart_json = json.loads(fig.to_json())

        summary_prompt = (
            f"Question: {state['question']}\nRules Checked:\n{state.get('rag_summary', '')}\n"
            f"Violating Records Found ({len(merged_rows)} rows): {merged_rows[:20]}\n"
            "List each violating record clearly with its exact values."
        )
        summary = llm.invoke(summary_prompt).content.strip()
        return {
            "sql_query": combined_sql,
            "sql_results": merged_rows,
            "sql_error": last_error,
            "sql_attempts": 1,
            "sql_summary": summary,
            "chart_json": chart_json,
        }

    sql, rows, err = _run_single_sql(state["question"], schema)
    if err and not rows:
        return {
            "sql_query": "",
            "sql_results": [],
            "sql_error": err,
            "sql_attempts": 3,
            "sql_summary": f"SQL query failed after 3 attempts: {err}",
            "chart_json": None,
        }

    chart_json = None
    if rows and len(rows) > 1 and len(rows[0]) >= 2:
        df = pd.DataFrame(rows)
        cols = list(df.columns)
        fig = px.bar(df, x=cols[0], y=cols[1], title=state["question"][:60])
        chart_json = json.loads(fig.to_json())

    summary_prompt = (
        f"Question: {state['question']}\nSQL: {sql}\nResults (top 20): {rows[:20]}\n"
        "Provide a concise, factual summary listing the exact rows returned."
    )
    summary = llm.invoke(summary_prompt).content.strip()
    return {
        "sql_query": sql,
        "sql_results": rows,
        "sql_error": "",
        "sql_attempts": 1,
        "sql_summary": summary,
        "chart_json": chart_json,
    }


def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    parts = []
    if state.get("rag_summary"):
        parts.append(f"Policy Rules:\n{state['rag_summary']}")
    if state.get("sql_summary"):
        parts.append(f"SQL Query Results:\n{state['sql_summary']}")
    combined = "\n\n".join(parts)
    prompt = (
        f"Question: {state['question']}\n\nEvidence:\n{combined}\n\n"
        "Write a direct, clear, accurate final response strictly grounded in the evidence above. "
        "List every matching record from SQL Query Results and state which policy rule it violates."
    )
    answer = llm.invoke(prompt).content.strip()
    return {"answer": answer}


def self_evaluator_node(state: AgentState) -> Dict[str, Any]:
    prompt = (
        "Grade the groundedness of the Answer against the combined SQL Results and Policy Context on a scale of 1 to 5 "
        "(5 = every claim in the Answer is supported by either SQL Results or Policy Context, 1 = hallucinated).\n"
        f"SQL Results: {state.get('sql_results', [])[:10]}\n"
        f"Policy Context: {state.get('rag_context', '')}\n"
        f"Answer: {state.get('answer', '')}\n"
        "Return ONLY a single integer from 1 to 5."
    )
    raw = llm.invoke(prompt).content.strip()
    match = re.search(r"[1-5]", raw)
    score = int(match.group(0)) if match else 4
    return {"groundedness_score": score, "eval_attempts": state.get("eval_attempts", 0) + 1}


def route_after_router(state: AgentState) -> str:
    if state["route"] in ("POLICY_RAG", "HYBRID"):
        return "policy_rag"
    return "sql_analyst"


def route_after_rag(state: AgentState) -> str:
    if state["route"] == "HYBRID":
        return "sql_analyst"
    return "synthesizer"


def route_after_eval(state: AgentState) -> str:
    if state["groundedness_score"] < 4 and state["eval_attempts"] < 2:
        return "synthesizer"
    return END


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("sql_analyst", sql_analyst_node)
    graph.add_node("policy_rag", policy_rag_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("self_evaluator", self_evaluator_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {"sql_analyst": "sql_analyst", "policy_rag": "policy_rag"},
    )
    graph.add_conditional_edges(
        "policy_rag",
        route_after_rag,
        {"sql_analyst": "sql_analyst", "synthesizer": "synthesizer"},
    )
    graph.add_edge("sql_analyst", "synthesizer")
    graph.add_edge("synthesizer", "self_evaluator")
    graph.add_conditional_edges(
        "self_evaluator",
        route_after_eval,
        {"synthesizer": "synthesizer", END: END},
    )
    return graph.compile()


agent_app = build_graph()


def run_query(question: str) -> Dict[str, Any]:
    initial_state: AgentState = {
        "question": question,
        "route": "",
        "sql_query": "",
        "sql_results": [],
        "sql_error": "",
        "sql_attempts": 0,
        "sql_summary": "",
        "chart_json": None,
        "rag_context": "",
        "citations": [],
        "rag_summary": "",
        "policy_rules": [],
        "answer": "",
        "groundedness_score": 5,
        "eval_attempts": 0,
    }
    final_state = agent_app.invoke(initial_state)
    return {
        "answer": final_state.get("answer", ""),
        "route": final_state.get("route", ""),
        "sql_query": final_state.get("sql_query", ""),
        "sql_results": final_state.get("sql_results", []),
        "chart_json": final_state.get("chart_json"),
        "citations": final_state.get("citations", []),
        "groundedness_score": final_state.get("groundedness_score", 0),
    }
