import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_pick import pick_llm
from utils.etl_tools import ETLTools
from models.schema import ETLAgentState
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool


@tool
def extract_load_tool(
    url: str,
    output_folder: str,
    file_format: str
) -> str:
    """
    Extracts data from the given URL and loads it into the specified output folder.

    Args:
        url: The URL to extract data from.
        output_folder: The folder to save the extracted data.
        file_format: The format of the extracted data (e.g., 'json', 'csv').
    Returns:
        A message indicating the success or failure of the operation.   
        """

    etl_tools = ETLTools()
    return etl_tools.extract_load(url, output_folder, file_format)


@tool
def transform_load_tool(file_path: str, output_folder: str, transformation_logic: str) -> str:
    """
    Transforms data from the given file and loads it into the specified output folder.

    Args:
        file_path: The path to the file to transform.
        output_folder: The folder to save the transformed data.
        transformation_logic: The logic to apply for transforming the data.