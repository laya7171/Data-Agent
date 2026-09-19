from utils.llm_pick import pick_llm
from models.schema import AgentState, JudgeSchema
from langchain_core.messages import AIMessage, HumanMessage
from utils.database import DatabaseUtil
from langgraph.graph import StateGraph, START, END
from rich import print


# ---------------------------------------------------------
# 1. CURATE QUESTION
# ---------------------------------------------------------

def curate_question(state: AgentState) -> AgentState:
    """
    Curates the question based on the provided context
    and updates AgentState.
    """

    user_question = state.user_question
    llm = pick_llm("low")

    response = llm.invoke(
        f"Curate the following question: {user_question}"
    )

    content = response.content

    if isinstance(content, list):
        content = "".join(
            block.get("text", "")
            if isinstance(block, dict)
            else str(block)
            for block in content
        )

    state.curated_question = content

    return state


# ---------------------------------------------------------
# 2. ADD DATABASE SCHEMA CONTEXT
# ---------------------------------------------------------

def prompt_query_context(state: AgentState) -> AgentState:
    """
    Creates the prompt containing the database schema
    and the curated user question.
    """

    curated_question = state.curated_question

    obj = DatabaseUtil()
    schema_info = obj.schema_details()

    prompt = f"""
You are an SQL analyst agent.

Your task is to convert the user's natural language query
into an SQLite3 query that can be executed on the database.

You are provided with the user's question and the database
schema, including table names, column names, data types,
and sample data.

Unless the user explicitly asks for a specific number of rows,
always limit the output to 10 rows.

IMPORTANT:
- Only generate SQL.
- Do not provide explanations.
- Do not use markdown code blocks.
- The output must be directly executable SQL.
- Do not modify the database.

User's question:
{curated_question}

Schema information:
{schema_info}
"""

    state.prompt_query_context = prompt

    return state


# ---------------------------------------------------------
# 3. GENERATE SQL
# ---------------------------------------------------------

def generate_sql(state: AgentState) -> AgentState:
    """
    Generates SQL from the database-aware prompt.
    """

    prompt = state.prompt_query_context
    llm = pick_llm("low")

    response = llm.invoke(prompt)

    content = response.content

    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )

    state.generated_sql_query = content.strip()

    return state


# ---------------------------------------------------------
# 4. CHECK SQL SAFETY
# ---------------------------------------------------------

def is_safe_sqlite(state: AgentState) -> AgentState:
    """
    Uses an LLM judge to determine whether the generated
    SQL query is safe to execute.
    """

    sql_query = state.generated_sql_query

    llm = pick_llm("low")

    llm_judge = llm.with_structured_output(JudgeSchema)

    prompt = f"""
You are an SQL security judge.

Determine whether the following SQL query is safe to execute.

The SQL query must ONLY retrieve data.

It must NOT modify the database.

Unsafe operations include:
- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- TRUNCATE
- CREATE
- REPLACE
- ATTACH
- DETACH
- PRAGMA modifications
- Any other command that modifies database data or structure

If the query only retrieves data, return:

is_safe = "Yes"

Otherwise return:

is_safe = "No"

Also provide a short explanation in comments.

SQL query:

{sql_query}
"""

    response = llm_judge.invoke(prompt)

    # Since JudgeSchema is a Pydantic model
    state.is_safe = response.is_safe
    state.comments = response.comments

    return state


# ---------------------------------------------------------
# 5. CANCEL UNSAFE SQL
# ---------------------------------------------------------

def canceled_sql(state: AgentState) -> AgentState:
    """
    Stops execution when the generated SQL is unsafe.
    """

    comments = state.comments


    state.final_answer = (
        "The generated SQL query was deemed unsafe to execute. "
        f"The reason provided by the judge is: {comments}"
    )

    return state


# ---------------------------------------------------------
# 6. EXECUTE SQL
# ---------------------------------------------------------

def execute_sql(state: AgentState) -> AgentState:
    """
    Executes the SQL query after it has been approved
    by the safety judge.
    """

    sql_query = state.generated_sql_query

    obj = DatabaseUtil()

    result = obj.execute_sql(sql_query)

    state.sql_query_execution_result = result

    return state


# ---------------------------------------------------------
# 7. GENERATE FINAL HUMAN-READABLE ANSWER
# ---------------------------------------------------------

def representaion_node(state: AgentState) -> AgentState:
    """
    Converts the SQL execution result into a
    human-readable final answer.
    """

    execution_result = state.sql_query_execution_result

    # FIXED TYPO:
    # state.crated_question ❌
    # state.curated_question ✅
    curated_question = state.curated_question

    llm = pick_llm("low")

    prompt = f"""
You are an SQL analyst agent.

Provide a final answer to the user's question based on
the SQL execution result.

The answer should:
- Be concise.
- Be clear.
- Directly answer the user's question.
- Avoid SQL code.
- Avoid technical implementation details.
- Be easy for a normal user to understand.

If the execution result is empty or does not provide
a clear answer, explain that clearly.

Execution result:
{execution_result}

User's question:
{curated_question}
"""

    response = llm.invoke(prompt)

    content = response.content

    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )

    state.final_answer = content

    return state


# ---------------------------------------------------------
# 8. CONDITIONAL ROUTER
# ---------------------------------------------------------

def is_safe_sql_edge(state: AgentState):
    """
    Routes the workflow based on the SQL safety decision.
    """

    if state.is_safe == "Yes":
        return "execute_sql"

    elif state.is_safe == "No":
        return "canceled_sql"

    else:
        raise ValueError(
            f"Invalid SQL safety state: {state.is_safe}"
        )


# ---------------------------------------------------------
# 9. BUILD GRAPH
# ---------------------------------------------------------

sql_agent_graph = StateGraph(AgentState)


# Nodes
sql_agent_graph.add_node(
    "curate_question",
    curate_question
)

sql_agent_graph.add_node(
    "prompt_query_context",
    prompt_query_context
)

sql_agent_graph.add_node(
    "generate_sql",
    generate_sql
)

sql_agent_graph.add_node(
    "is_safe_sqlite",
    is_safe_sqlite
)

sql_agent_graph.add_node(
    "canceled_sql",
    canceled_sql
)

sql_agent_graph.add_node(
    "execute_sql",
    execute_sql
)

sql_agent_graph.add_node(
    "representaion_node",
    representaion_node
)


# ---------------------------------------------------------
# EDGES
# ---------------------------------------------------------

sql_agent_graph.add_edge(
    START,
    "curate_question"
)

sql_agent_graph.add_edge(
    "curate_question",
    "prompt_query_context"
)

sql_agent_graph.add_edge(
    "prompt_query_context",
    "generate_sql"
)

sql_agent_graph.add_edge(
    "generate_sql",
    "is_safe_sqlite"
)


# Conditional edge
sql_agent_graph.add_conditional_edges(
    "is_safe_sqlite",
    is_safe_sql_edge,
    {
        "execute_sql": "execute_sql",
        "canceled_sql": "canceled_sql"
    }
)


sql_agent_graph.add_edge(
    "execute_sql",
    "representaion_node"
)

sql_agent_graph.add_edge(
    "canceled_sql",
    END
)

sql_agent_graph.add_edge(
    "representaion_node",
    END
)


# ---------------------------------------------------------
# COMPILE
# ---------------------------------------------------------

sql_analyst = sql_agent_graph.compile()


# ---------------------------------------------------------
# TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    initial_state = AgentState(
    user_question="Give me top highest payment giving users in the database",
    curated_question="",
    prompt_query_context="",
    generated_sql_query="",
    is_safe=None,
    final_answer="",
    comments="",
    sql_query_execution_result=""
)
    res = sql_analyst.invoke(initial_state)

    print("\n==============================")
    print("FINAL STATE")
    print("==============================")

    print(res)

    print("\n==============================")
    print("FINAL ANSWER")
    print("==============================")

    # If LangGraph returns a dict
    if isinstance(res, dict):
        print(res["final_answer"])
    else:
        print(res.final_answer)