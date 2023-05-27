# -*- coding: utf-8 -*-
from starlette_wtf import StarletteForm
from wtforms import TextAreaField
from wtforms import validators
from wtforms.validators import ValidationError

# Define the maximum number of rows allowed
max_rows = 500  # Adjust the value as needed

class RequirementsForm(StarletteForm):
    """Requirements Upload"""

    requirements = TextAreaField(
        "Requirements",
        render_kw={"rows": max_rows},
        validators=[
            validators.DataRequired("Paste requirements.txt here"),
        ],
    )

    def validate_requirements(self, field):
        # Count the number of lines in the textarea
        num_lines = field.data.count('\n') + 1

        # Validate the number of rows
        if num_lines > max_rows:
            raise ValidationError(f"Maximum number of {max_rows} rows exceeded.")
        