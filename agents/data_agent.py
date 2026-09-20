from utils.llm_pick import pick_llm
from models.schema import (
    DataAgentSchema,
    DataAgentState,
    AgentState
)

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst

from langchain_core.messages import (
    HumanMessage,
    AIMessage
)


# ============================================================
# LLM ROUTER
# ============================================================

llm = pick_llm("low")

llm_router = llm.with_structured_output(
    DataAgentSchema
)


# ============================================================
# ROUTER NODE
# ============================================================

def decider_node(state: DataAgentState):

    # Get user's latest message
    message = state.messages[-1].content

    # Ask LLM which sub-agent should handle it
    route_response = llm_router.invoke(message)

    # Return state update
    return {
        "route_response": route_response.answer
    }


# ============================================================
# ETL NODE
# ============================================================

def etl_node(state: DataAgentState):

    # Get user's message
    message = state.messages[-1].content

    # Run ETL sub-agent
    response = etl_analyst.invoke(
        {
            "user_question": message
        }
    )

    # Get the final answer from ETL agent
    #
    # LangGraph compiled graph normally returns a dict
    # containing the sub-agent's state.
    #
    # We want to send only its final message back
    # to the main Data Agent.

    final_message = response["messages"][-1]

    return {
        "messages": [
            final_message
        ]
    }


# ============================================================
# SQL NODE
# ============================================================

def sql_node(state: DataAgentState):

    # Get user's message
    message = state.messages[-1].content

    # Create the SQL sub-agent's state
    initial_state = AgentState(
        user_question=message,
        curated_question="",
        prompt_query_context="",
        generated_sql_query="",
        is_safe=None,
        final_answer="",
        comments="",
        sql_query_execution_result=""
    )

    # Run SQL sub-agent
    response = sql_analyst.invoke(
        initial_state
    )

    # Return SQL agent's final answer
    return {
        "messages": [
            AIMessage(
                content=response["final_answer"]
            )
        ]
    }


# ============================================================
# CREATE MAIN DATA AGENT GRAPH
# ============================================================

data_agent_graph = StateGraph(
    DataAgentState
)


# ============================================================
# ADD NODES
# ============================================================

data_agent_graph.add_node(
    "router_node",
    decider_node
)

data_agent_graph.add_node(
    "etl_node",
    etl_node
)

data_agent_graph.add_node(
    "sql_node",
    sql_node
)


# ============================================================
# START → ROUTER
# ============================================================

data_agent_graph.add_edge(
    START,
    "router_node"
)


# ============================================================
# ROUTER
# ============================================================

def route_edge(state: DataAgentState):

    if state.route_response == "etl":
        return "etl_node"

    elif state.route_response == "sql":
        return "sql_node"

    else:
        raise ValueError(
            f"Invalid route response: "
            f"{state.route_response}"
        )


# ============================================================
# ROUTER → SUB-AGENT
# ============================================================

data_agent_graph.add_conditional_edges(
    "router_node",
    route_edge,
    {
        "etl_node": "etl_node",
        "sql_node": "sql_node"
    }
)


# ============================================================
# SUB-AGENT → END
# ============================================================

data_agent_graph.add_edge(
    "etl_node",
    END
)

data_agent_graph.add_edge(
    "sql_node",
    END
)


# ============================================================
# COMPILE
# ============================================================

data_agent = data_agent_graph.compile()


# ============================================================
# VISUALIZE GRAPH
# ============================================================

if __name__ == "__main__":

    from IPython.display import (
        display,
        Image
    )

    img = Image(
    data_agent
    .get_graph()
    .draw_mermaid_png()
)
    with open(
        "data_agent_graph.png",
        "wb"
    ) as f:
        f.write(img.data)

    display(img)


    # ========================================================
    # INITIAL STATE
    # ========================================================

    initial_state = DataAgentState(
        messages=[
            HumanMessage(
                content=(
                    "I want to extract data from "
                    "https://pokeapi.co/api/v2/pokemon?limit=10 "
                    "and save it in JSON format in the "
                    "'data' folder."
                )
            )
        ],
        route_response=""
    )


    # ========================================================
    # RUN DATA AGENT
    # ========================================================

    response = data_agent.invoke(
        initial_state
    )


    # ========================================================
    # PRINT RESULT
    # ========================================================

    print(
        "\n=============================="
    )

    print(
        "FINAL RESPONSE"
    )

    print(
        "=============================="
    )

    print(response)