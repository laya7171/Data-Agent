import os
import sys

# Add project root to Python path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from utils.llm_pick import pick_llm
from utils.etl_tools import ETLTools
from models.schema import ETLAgentState

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from langchain_core.tools import tool

from langgraph.graph import StateGraph, START, END


# ============================================================
# TOOLS
# ============================================================

@tool
def extract_load_tool(
    url: str,
    output_folder: str,
    file_format: str
) -> str:
    """
    Extract data from a URL and save it to the specified
    output folder in the requested format.

    Args:
        url: URL from which data should be extracted.
        output_folder: Folder where the extracted data should be saved.
        file_format: Output format such as json or csv.

    Returns:
        A message describing the result of the operation.
    """

    etl_tools = ETLTools()

    return etl_tools.extract_load(
        url,
        output_folder,
        file_format
    )


@tool
def transform_load_tool(
    file_path: str,
    output_folder: str,
    output_format: str,
    user_question: str
) -> str:
    """
    Transform data from a file according to the user's question
    and save the transformed data to the desired location.

    Args:
        file_path: Path to the input file.
        output_folder: Folder where transformed data should be saved.
        output_format: Output format such as json or csv.
        user_question: User's ETL request.

    Returns:
        A message describing the result of the operation.
    """

    etl_tools = ETLTools()

    # Get a small amount of context from the input file
    top_3_rows = etl_tools.transform_load_context(file_path)

    # Use a low-cost LLM to generate Pandas code
    llm = pick_llm("low")

    prompt = f"""
You are a Python Data Analyst who uses Pandas to analyze data.

Your task is to generate ONLY executable Pandas/Python code
that transforms the data stored in:

{file_path}

according to the user's question.

Rules:
- Return ONLY Python code.
- Do not provide explanations.
- Do not use Markdown.
- Do not use ```python.
- The code must create a Pandas DataFrame from the input file.
- Perform the required transformation.
- Save the transformed result to:
  {output_folder}
- The output format should be:
  {output_format}

User question:
{user_question}

Context from the input data:
{top_3_rows}
"""

    response = llm.invoke(prompt)

    # Handle LangChain response content
    pandas_code = response.content.strip()

    # Remove markdown code fences if the model accidentally adds them
    if pandas_code.startswith("```python"):
        pandas_code = pandas_code[len("```python"):]

    elif pandas_code.startswith("```"):
        pandas_code = pandas_code[len("```"):]

    if pandas_code.endswith("```"):
        pandas_code = pandas_code[:-3]

    pandas_code = pandas_code.strip()

    # Execute generated Pandas code
    results = etl_tools.execute_code(pandas_code)

    return (
        f"The data was transformed and saved to "
        f"{output_folder} in {output_format} format. "
        f"Execution Results: {results}"
    )


# ============================================================
# TOOL LIST
# ============================================================

tools = [
    extract_load_tool,
    transform_load_tool,
]


# ============================================================
# LLM
# ============================================================

llm = pick_llm("low")

llm_with_tools = llm.bind_tools(tools)


# ============================================================
# LLM NODE
# ============================================================

def llm_node(state: ETLAgentState) -> dict:

    if not state.messages:
        messages = [
            HumanMessage(
                content=state.user_question
            )
        ]
        response = llm_with_tools.invoke(messages)
        return {
            "messages": [response]
        }

    last_message = state.messages[-1]

    if getattr(last_message, "type", "") == "tool":
        final_prompt = (
            "Use the tool result to answer the user's request. "
            f"User request: {state.user_question}\n\n"
            f"Tool result:\n{last_message.content}"
        )
        response = llm.invoke([HumanMessage(content=final_prompt)])
        return {
            "messages": [response]
        }

    response = llm_with_tools.invoke(state.messages)

    return {
        "messages": [response]
    }

# ============================================================
# TOOL NODE
# ============================================================

def tool_node(state: ETLAgentState) -> dict:

    tools_by_name = {
        tool.name: tool
        for tool in tools
    }

    last_message = state.messages[-1]

    tool_calls = getattr(
        last_message,
        "tool_calls",
        []
    )

    tool_results = []

    for tool_call in tool_calls:

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        tool = tools_by_name.get(tool_name)

        if tool is None:

            tool_results.append(
                ToolMessage(
                    content=f"Tool '{tool_name}' was not found.",
                    tool_call_id=tool_call["id"]
                )
            )

            continue

        try:

            result = tool.invoke(tool_args)

            tool_results.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                )
            )

        except Exception as e:

            tool_results.append(
                ToolMessage(
                    content=f"Tool execution failed: {str(e)}",
                    tool_call_id=tool_call["id"]
                )
            )

    return {
        "messages": tool_results
    }


# ============================================================
# ROUTER
# ============================================================

def is_tool_call(state: ETLAgentState):

    if not state.messages:
        return "end"

    last_message = state.messages[-1]

    if getattr(last_message, "tool_calls", []):
        return "tool_node"

    if getattr(last_message, "type", "") == "tool":
        return "end"

    return "end"


# ============================================================
# BUILD GRAPH
# ============================================================

etl_analyst_graph = StateGraph(ETLAgentState)

etl_analyst_graph.add_node(
    "llm_node",
    llm_node
)

etl_analyst_graph.add_node(
    "tool_node",
    tool_node
)

etl_analyst_graph.add_edge(
    START,
    "llm_node"
)

etl_analyst_graph.add_conditional_edges(
    "llm_node",
    is_tool_call,
    {
        "tool_node": "tool_node",
        "end": END
    }
)

etl_analyst_graph.add_edge(
    "tool_node",
    "llm_node"
)

etl_analyst = etl_analyst_graph.compile()

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":

    # --------------------------------------------------------
    # Visualize graph
    # --------------------------------------------------------

    try:

        from IPython.display import display, Image

        img = Image(
    etl_analyst
    .get_graph()
    .draw_mermaid_png()
)

        with open(
            "etl_analyst_graph.png",
            "wb"
        ) as f:

            f.write(img.data)

        display(img)

    except Exception as e:

        print(
            f"Graph visualization skipped: {e}"
        )


    # --------------------------------------------------------
    # User request
    # --------------------------------------------------------

    user_question = """
Extract data from
https://pokeapi.co/api/v2/pokemon?limit=10
and save it in JSON format in the 'data' folder.
"""

    # --------------------------------------------------------
    # Run graph
    # --------------------------------------------------------

    response = etl_analyst.invoke(
        {
            "user_question": (
                "Extract data from "
                "https://pokeapi.co/api/v2/pokemon?limit=10 "
                "and save it in JSON format in the 'data' folder."
            )
        }
    )

    print(response)