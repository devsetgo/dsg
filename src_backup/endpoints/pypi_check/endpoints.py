# -*- coding: utf-8 -*-
import uuid
from datetime import datetime

from loguru import logger
from starlette.responses import RedirectResponse
from starlette_wtf import csrf_protect

from endpoints.pypi_check import forms
from endpoints.pypi_check import library_data
from endpoints.pypi_check import pypi_calls  # import main, process_raw
from endpoints.pypi_check.crud import get_request_group_id
from endpoints.pypi_check.crud import store_in_data
from resources import templates

base: str = "pypi"


# URL /pypi/dashboard
async def pypi_data(request):
    """
    Returns a TemplateResponse object that renders the 'pypi/dashboard.html' template with data from the library table,
    requirements table, and latest results.

    Args:
        request: A Starlette Request object representing the incoming HTTP request.

    Returns:
        A TemplateResponse object that renders the 'pypi/dashboard.html' template with the following context variables:
            - request: The original request object.
            - data: A dictionary containing data from the library table, requirements table, and latest results.
    """

    # Get data from the library table
    lib_data = await library_data.get_data()

    # Get data from the requirements table
    req_data = await library_data.requests_data()

    # Get the latest results
    latest_results = await library_data.latest_results()

    # Combine all the data into a single dictionary
    data: dict = {
        "req_data": req_data,
        "lib_data": lib_data,
        "latest_results": latest_results,
    }

    # Log the data for debugging purposes
    logger.debug(data)

    # Set the name of the template to render
    template: str = "pypi/dashboard.html"

    # Create the context dictionary to pass to the template
    context = {"request": request, "data": data}

    # Log that the page was accessed and the headers of the request
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))

    # Return a TemplateResponse object that renders the specified template with the given context
    return templates.TemplateResponse(template, context)


# URL /pypi/check
@csrf_protect
async def pypi_index(request):
    """
    View function for the PyPI check page.

    This view function receives a POST request with form data containing a list of package requirements.
    It validates the form data and processes it by calling the `process_raw` and `clean_item` functions from the
    `pypi_calls` module. It then calls the `loop_calls_adv` function to get information about each package from PyPI.
    Finally, it stores the incoming and outgoing data in the database and redirects the user to the results page.

    Args:
        request: An instance of the `Request` class representing the incoming HTTP request.

    Returns:
        A `RedirectResponse` object that redirects the user to the results page if the form is valid, or a
        `TemplateResponse` object that renders the PyPI check page with the form if the form is invalid.
    """
    # Create an instance of the RequirementsForm class from the incoming form data
    form = await forms.RequirementsForm.from_formdata(request)
    # Get the form data as a dictionary
    form_data = await request.form()

    # Validate the form data
    if await form.validate_on_submit():
        # Log the requirements string
        logger.debug(f'requirements: {form_data["requirements"]}')
        # Get the requirements string from the form data
        requirements_str = form_data["requirements"]

        # Set the raw data to the requirements string
        raw_data: str = requirements_str
        # Generate a UUID for the request group
        request_group_id = uuid.uuid4()
        # Store the incoming data in the database
        # Process the raw data using the `process_raw` function from the `pypi_calls` module
        req_list = await pypi_calls.process_raw(raw_data=raw_data)
        # Clean the processed data using the `clean_item` function from the `pypi_calls` module
        cleaned_data = pypi_calls.clean_item(req_list)
        # Call the `loop_calls_adv` function from the `pypi_calls` module to get information about each package from PyPI
        fulllist = await pypi_calls.loop_calls_adv(
            itemList=cleaned_data, request_group_id=str(request_group_id)
        )
        # Store the returned results in the database
        values = {
            "id": str(uuid.uuid4()),
            "request_group_id": str(request_group_id),
            "text_in": raw_data,
            "json_data_in": req_list,
            "json_data_out": fulllist,
            "lib_out_count": len(fulllist),
            "host_ip": request.client.host,
            "header_data": dict(request.headers),
            "date_created": datetime.now(),
        }
        await store_in_data(values)

        # Redirect the user to the results page
        logger.info("Redirecting user to index page /")
        return RedirectResponse(
            url=f"/pypi/results/{str(request_group_id)}", status_code=303
        )

    # If the form is invalid, render the PyPI check page with the form
    status_code = 200
    template = f"/{base}/pypi_new.html"
    context = {"request": request, "form": form}
    logger.info("page accessed: /pypi/")
    return templates.TemplateResponse(template, context, status_code=status_code)


# URL /pypi/results/{UUID}
async def pypi_result(request):
    """
    View function for the PyPI results page.

    This view function receives a GET request with a UUID parameter representing the ID of the request group.
    It retrieves the data associated with the request group from the database using the `get_request_group_id`
    function, and renders the results page with the retrieved data.

    Args:
        request: An instance of the `Request` class representing the incoming HTTP request.

    Returns:
        A `TemplateResponse` object that renders the PyPI results page with the retrieved data.
    """
    # Get the UUID parameter from the request path parameters
    request_group_id = request.path_params["page"]
    # Get the data associated with the request group from the database
    data = await get_request_group_id(request_group_id=request_group_id)
    logger.debug(data)
    # Render the results page with the retrieved data
    template = f"/{base}/result.html"
    context = {"request": request, "data": data}
    logger.info(f"page accessed: /pypi/{request_group_id}")
    return templates.TemplateResponse(template, context)
