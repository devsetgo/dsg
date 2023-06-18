# -*- coding: utf-8 -*-

from loguru import logger
from starlette.responses import RedirectResponse

from endpoints.main import crud as lib_crud
from endpoints.main.functions import call_github_repos
from endpoints.main.functions import call_github_user
from resources import cool_stuff

# from resources import my_stuff
from resources import templates


# URL /
async def homepage(request):
    """
    This function handles requests to the root URL (`/`). It redirects the user to the `/index` URL using a 303 status code.

    Args:
        request: The incoming HTTP request object.

    Returns:
        A `RedirectResponse` object that redirects the user to the `/index` URL.
    """

    # Create a `RedirectResponse` object that redirects the user to the `/index` URL using a 303 status code.
    return RedirectResponse(url="/index", status_code=303)


# URL /about
async def about_page(request):
    """
    This function handles requests to the /about URL. It calls the `call_github_repos` and `call_github_user`
    functions to retrieve data from GitHub, and then returns a template response containing that data.

    Args:
        request: The incoming HTTP request object.

    Returns:
        A `TemplateResponse` object containing the rendered HTML template and the retrieved data.
    """

    # Retrieve data from GitHub using the `call_github_repos` and `call_github_user` functions.
    data_repo = await call_github_repos()
    data_user = await call_github_user()

    # Combine the retrieved data into a single dictionary.
    data: dict = {"data_repo": data_repo, "data_user": data_user}

    # Define the name of the HTML template to use for this page.
    template: str = "about.html"

    # Define the context variables to pass to the template.
    context = {"request": request, "data": data}

    # Log some information about the request.
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))

    # Return a `TemplateResponse` object containing the rendered HTML template and the retrieved data.
    return templates.TemplateResponse(template, context)


# URL /index
async def index(request):
    """
    This function handles requests to the /index URL. It calls the `call_github_repos` function to retrieve data from GitHub,
    and then returns a template response containing that data.

    Args:
        request: The incoming HTTP request object.

    Returns:
        A `TemplateResponse` object containing the rendered HTML template and the retrieved data.
    """

    # Retrieve data from GitHub using the `call_github_repos` function.
    my_stuff = await call_github_repos()

    # Combine the retrieved data into a single dictionary.
    data: dict = {"my_stuff": my_stuff, "cool_stuff": cool_stuff}

    # Define the name of the HTML template to use for this page.
    template: str = "index2.html"

    # Define the context variables to pass to the template.
    context = {"request": request, "data": data}

    # Log some information about the request.
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))

    # Return a `TemplateResponse` object containing the rendered HTML template and the retrieved data.
    return templates.TemplateResponse(template, context)


# URL /users/login
async def login(request):
    """
    This function handles requests to the `/users/login` URL. It returns a `TemplateResponse` object that renders the `users/login.html` template.

    Args:
        request: The incoming HTTP request object.

    Returns:
        A `TemplateResponse` object that renders the `users/login.html` template.
    """

    # Define the path to the login template.
    template: str = "users/login.html"

    # Define the context data to pass to the template.
    context = {"request": request, "data": None}

    # Log information about the page access and request headers.
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))

    # Return a `TemplateResponse` object that renders the login template with the given context data.
    return templates.TemplateResponse(template, context)
