import os
import requests
import pandas as pd


class ETLTools:

    def __init__(self):
        pass

    def extract_load(
        self,
        url: str,
        output_folder: str,
        file_format: str
    ) -> str:
        """
        Extracts data from an API and loads it into the desired location.

        Args:
            url: The API endpoint from which to extract data.
            output_folder: The folder where the extracted data will be saved.
            file_format: The format to save the data.
                         Supported: csv, json, parquet.

        Returns:
            A message indicating the success or failure of the operation.
        """

        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        output_folder = os.path.join(
            project_root,
            output_folder
        )

        try:
            # -------------------------
            # EXTRACT
            # -------------------------
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # -------------------------
            # LOAD
            # -------------------------
            os.makedirs(
                output_folder,
                exist_ok=True
            )

            filename = os.path.join(
                output_folder,
                f"extracted_data.{file_format}"
            )

            # PokeAPI returns:
            # {
            #     "count": ...,
            #     "next": ...,
            #     "previous": ...,
            #     "results": [...]
            # }
            #
            # So we extract only the actual records.
            if isinstance(data, dict) and "results" in data:
                data = data["results"]

            df = pd.json_normalize(data)

            if file_format == "csv":
                df.to_csv(
                    filename,
                    index=False
                )

            elif file_format == "json":
                df.to_json(
                    filename,
                    orient="records",
                    lines=True
                )

            elif file_format == "parquet":
                df.to_parquet(
                    filename,
                    index=False
                )

            else:
                return (
                    f"Unsupported format: {file_format}. "
                    f"Use csv, json, or parquet."
                )

            return (
                f"Data successfully extracted "
                f"and saved to {filename}"
            )

        except requests.exceptions.RequestException as e:
            return f"Failed to extract data: {e}"

        except ValueError as e:
            return f"Failed to process response data: {e}"

        except Exception as e:
            return f"Unexpected error: {e}"


    def transform_load_context(self, file_path: str) -> str:
        """
        Reads an extracted data file and returns the first 3 rows
        as context for the agent.

        Args:
            file_path: Path to the data file.

        Returns:
            The first 3 rows of the dataset.
        """

        file_extension = os.path.splitext(
            file_path
        )[1].lower()

        try:

            if file_extension == ".csv":
                df = pd.read_csv(file_path)

            elif file_extension == ".json":
                df = pd.read_json(
                    file_path,
                    lines=True
                )

            elif file_extension == ".parquet":
                df = pd.read_parquet(file_path)

            else:
                return (
                    f"Unsupported file format: "
                    f"{file_extension}"
                )

            top_3_rows = str(
                df.head(3)
            )

            return top_3_rows

        except Exception as e:
            return f"Failed to read file: {e}"


    def execute_code(self, code: str) -> str:
        """
        Executes the provided Python code.

        Args:
            code: Python code to execute.

        Returns:
            The output or error message.
        """

        try:
            exec(code)

            return "Code executed successfully."

        except Exception as e:
            return f"Failed to execute code: {e}"


if __name__ == "__main__":

    etl_tools = ETLTools()

    # -------------------------
    # EXTRACT + LOAD
    # -------------------------

    url = "https://pokeapi.co/api/v2/pokemon?limit=10"

    output_folder = "data"

    file_format = "json"

    result = etl_tools.extract_load(
        url,
        output_folder,
        file_format
    )

    print(result)

    # -------------------------
    # TRANSFORM / CONTEXT
    # -------------------------

    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )

    file_path = os.path.join(
        project_root,
        output_folder,
        f"extracted_data.{file_format}"
    )

    print("\nFirst 3 rows:")
    print(
        etl_tools.transform_load_context(
            file_path
        )
    )
    