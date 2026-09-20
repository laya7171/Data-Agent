import streamlit as st

from langchain_core.messages import HumanMessage

from agents.data_agent import data_agent
from models.schema import DataAgentState


st.set_page_config(
    page_title="Data Agent",
    page_icon="🤖",
    layout="wide",
)


@st.cache_resource

def get_agent():
    return data_agent


def run_agent(prompt: str) -> str:
    agent = get_agent()

    initial_state = DataAgentState(
        messages=[HumanMessage(content=prompt)],
        route_response="",
    )

    try:
        result = agent.invoke(initial_state)
        messages = result.get("messages", [])

        if not messages:
            return "The agent did not return a response."

        last_message = messages[-1]

        if hasattr(last_message, "content"):
            content = last_message.content
            if isinstance(content, list):
                return "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in content
                )
            return str(content)

        return str(last_message)

    except Exception as exc:
        return f"Agent error: {exc}"


st.title("Data Agent")
st.caption("Enterprise-style ETL and SQL assistant for structured data workflows.")

with st.sidebar:
    st.header("Project Overview")
    st.markdown(
        """
        This assistant routes user requests between two specialized agents:

        - ETL Analyst: extracts data from web APIs and saves it to JSON/CSV/parquet
        - SQL Analyst: turns natural-language questions into safe SQLite queries
        """
    )

    st.markdown("### Example prompts")
    sample_prompts = [
        "Extract data from https://pokeapi.co/api/v2/pokemon?limit=10 and save it in JSON format in the data folder.",
        "Show me the top payment users in the database.",
        "Which users are active and where are they located?",
    ]

    for prompt in sample_prompts:
        if st.button(prompt, use_container_width=True):
            st.session_state.chat_input_value = prompt

    st.markdown("### Project Stack")
    st.write("Python • LangGraph • LangChain • SQLite • Streamlit • Pandas")


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "chat_input_value" not in st.session_state:
    st.session_state.chat_input_value = ""


chat_tab, overview_tab, architecture_tab = st.tabs([
    "Chat with Agent",
    "Project Overview",
    "Architecture & Screenshots",
])

with chat_tab:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(
        "Ask the agent to extract data or answer a SQL question...",
        key="agent_chat_input",
    )

    if st.session_state.chat_input_value:
        prompt = st.session_state.chat_input_value
        st.session_state.chat_input_value = ""

    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("The agent is processing your request..."):
            response = run_agent(prompt)

        st.session_state.chat_history.append({"role": "assistant", "content": response})

        with st.chat_message("assistant"):
            st.markdown(response)

        st.rerun()

with overview_tab:
    st.markdown(
        """
        ## What this project does

        The Data Agent combines two specialized workflows:

        1. ETL pipeline automation
           - Pulls structured data from public APIs
           - Saves outputs to local storage in CSV, JSON, or parquet
           - Prepares data for downstream analysis

        2. SQL analysis workflow
           - Converts natural language into SQLite-safe SQL
           - Validates that the query is read-only
           - Executes the query and returns a clear answer

        ## Why this is useful

        This gives you a single interface for both raw data acquisition and database querying.
        It is useful for demos, internal tools, and small-scale analytics workflows.
        """
    )

    st.markdown("### Core files")
    st.code(
        """
        agents/
        ├── etl_analyst.py
        ├── sql_analyst.py
        └── data_agent.py

        utils/
        ├── etl_tools.py
        ├── database.py
        ├── create_db.py
        └── llm_pick.py

        models/
        └── schema.py

        csv_data/
        data/
        """
    )

with architecture_tab:
    st.markdown("## Architecture and visual references")

    image_paths = [
        ("Architecture.png", "Overall project architecture"),
        ("ReAct_Agent_Architecture.png", "ReAct-style multi-agent design"),
        ("data_agent_graph.png", "Main router graph"),
        ("etl_analyst_graph.png", "ETL agent workflow"),
        ("sql_analyst_graph.png", "SQL agent workflow"),
        ("SQL_Analyst_Result.png", "Sample SQL workflow output"),
    ]

    cols = st.columns(2)
    for index, (image_path, caption) in enumerate(image_paths):
        with cols[index % 2]:
            st.image(image_path, caption=caption, use_container_width=True)


st.markdown("---")
st.caption("Built for demo presentations and interactive exploration of the Data Agent project.")
