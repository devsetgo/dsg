import re
from datetime import datetime
from typing import List

def get_current_datetime_version() -> str:
    """
    Get the current date and time in the format YYYY-MM-DD-HMS.

    Returns:
        str: The current date and time as a version string.
    """
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")

def update_version_in_files(new_version: str, files: List[str]) -> None:
    """
    Update the __version__ variable in the specified files.

    Args:
        new_version (str): The new version string.
        files (List[str]): List of file paths to update.
    """
    # Regex pattern to match the __version__ line
    version_pattern = re.compile(r'(__version__\s*=\s*["\'])([^"\']+)(["\'])')

    for file_path in files:
        with open(file_path, 'r') as file:
            content = file.read()
        # Replace the old version with the new version
        new_content = version_pattern.sub(r'\g<1>' + new_version + r'\3', content)

        with open(file_path, 'w') as file:
            file.write(new_content)

if __name__ == "__main__":
    # Get the new version
    new_version = get_current_datetime_version()

    # List of files to update
    files_to_update = [
        '/workspaces/dsg/src/__init__.py',
        # Add more file paths as needed
    ]

    # Update the version in the specified files
    update_version_in_files(new_version, files_to_update)

    print(f"Updated version to {new_version} in specified files.")