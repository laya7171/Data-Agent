from langchain_core.tools import tool
import os


class ETLTools:

    def __init__(self):
        pass

    def extract_data(self, url: str, output_folder: str)-> str:
        """
        Extracts data from the source like API, urls and loads it into the desired location "\n
        Args:
            url (str): The URL of the data source.
            output_folder (str): The folder where the extracted data will be saved.
        Returns:
            str: A message indicating the success of the extraction process.
        """

        project_root = os.path.abspath(os.path.dirname(__file__), '..')
        output_folder =os.path.join(project_root, output_folder)

        