# -*- coding: utf-8 -*-
import spacy
import os
import shutil
from pathlib import Path
import tempfile

# Define the target directory
target_dir = Path("/workspaces/dsg/spacy_models")

# Ensure the target directory exists
target_dir.mkdir(parents=True, exist_ok=True)

# Create a temporary directory for downloading the model
with tempfile.TemporaryDirectory() as temp_dir:
    temp_dir_path = Path(temp_dir)

    # Download the model to the temporary directory
    spacy.cli.download("xx_ent_wiki_sm")

    # Find the downloaded model directory using "starts with" approach
    default_model_dir = None
    for model_dir in temp_dir_path.iterdir():
        if model_dir.is_dir() and model_dir.name.startswith("xx_ent_wiki_sm"):
            default_model_dir = model_dir
            break

    if default_model_dir is None:
        print("Failed to find the downloaded model directory")
    else:
        # Define the final model directory name
        final_model_dir = target_dir / "xx_ent_wiki_sm"

        # Move and rename the model directory
        try:
            shutil.move(str(default_model_dir), str(final_model_dir))
            print(f"Model moved and renamed to {final_model_dir}")
        except Exception as e:
            print(f"Failed to move and rename the model: {e}")

        # Load the model from the target directory
        try:
            model = spacy.load(final_model_dir)
            print("Model loaded successfully")
        except Exception as e:
            print(f"Failed to load the model: {e}")
