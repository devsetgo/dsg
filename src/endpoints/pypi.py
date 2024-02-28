# -*- coding: utf-8 -*-

import uuid
from datetime import datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from sqlalchemy import Select, and_, func
from sqlalchemy.orm import joinedload

from ..db_tables import Library, LibraryName, Requirement
from ..functions.pypi_core import check_packages
from ..resources import db_ops, templates

router = APIRouter()


# create index page route
@router.get("/", response_class=RedirectResponse)
async def root():
    """
    Root endpoint of API
    Returns:
        Redrects to openapi document
    """
    # redirect to openapi docs
    logger.info("Redirecting to OpenAPI docs")
    return RedirectResponse(url="/pypi/index")



@router.get("/index")
async def index(request: Request):
    total_libraries = await db_ops.count_query(query=Select(LibraryName))
    # most_common_libraries = [
    #     {"name": library[0], "count": library[1]}
    #     for library in await db_ops.read_query(
    #         query=Select(
    #             LibraryName.name, func.count(Library.library_id).label("count")
    #         )
    #         .select_from(Library)
    #         .join(LibraryName, Library.library_id == LibraryName.pkid)
    #         .group_by(LibraryName.name)
    #         .order_by(func.count(Library.library_id).desc())
    #         .limit(10)
    #     )
    # ]
    most_common_libraries = await most_common_library()

    libraries_with_most_vulnerabilities = [
        library.to_dict()
        for library in await db_ops.read_query(
            query=Select(Library)
            .where(Library.new_version_vulnerability == True)
            .options(joinedload(Library.library))
            .group_by(Library.library_id)
            .order_by(func.count(Library.library_id).desc())
            .limit(10)
        )
    ]

    libraries_per_request_group = await db_ops.count_query(
        query=Select(Library.request_group_id)
        .group_by(Library.request_group_id)
        .order_by(func.count(Library.request_group_id).desc())
        .limit(10)
    )
    libraries_with_new_versions = await db_ops.count_query(
        query=Select(Library).where(Library.current_version != Library.new_version)
    )
    total_requirements = await db_ops.count_query(query=Select(Requirement))
    requirements_by_host_ip = await db_ops.count_query(
        query=Select(Requirement.host_ip)
        .group_by(Requirement.host_ip)
        .order_by(func.count(Requirement.host_ip).desc())
        .limit(10)
    )
    most_common_user_agents = await db_ops.count_query(
        query=Select(Requirement.user_agent)
        .group_by(Requirement.user_agent)
        .order_by(func.count(Requirement.user_agent).desc())
        .limit(10)
    )
    # average_number_of_libraries_per_requirement = await db_ops.count_query(
    #     query=Select(
    #         func.avg((Requirement.lib_in_count + Requirement.lib_out_count) / 2)
    #     )
    # )

    total_number_of_vulnerabilities = await db_ops.count_query(
        query=Select(Library).where(Library.vulnerability != None)
    )
    last_one_hundred_requests = [
        requirement.to_dict()
        for requirement in await db_ops.read_query(
            query=Select(Requirement).order_by(Requirement.date_created.desc()).limit(1)
        )
    ]

    library_name = [
        library.to_dict()
        for library in await db_ops.read_query(query=Select(LibraryName).limit(100))
    ]
    context = {
        "total_libraries": total_libraries,
        "libraries_per_request_group": libraries_per_request_group,
        "libraries_with_new_versions": libraries_with_new_versions,
        "total_requirements": total_requirements,
        "requirements_by_host_ip": requirements_by_host_ip,
        "most_common_user_agents": most_common_user_agents,
        "average_number_of_libraries_per_requirement": await average_number_of_libraries_per_requirement(),
        "total_number_of_vulnerabilities": total_number_of_vulnerabilities,
        "most_common_libraries": most_common_libraries,
        "libraries_with_most_vulnerabilities": libraries_with_most_vulnerabilities,
        "last_one_hundred_requests": last_one_hundred_requests,
        "library_name": library_name,
    }
    return templates.TemplateResponse(
        request=request, name="/pypi/dashboard.html", context=context
    )




async def most_common_library():
    # Calculate the date one year ago from the current date and time
    # This is done by subtracting 365 days from the current date and time
    one_year_ago = datetime.now() - timedelta(days=365)

    # Query the Library table for entries from the last year
    # The query selects all entries from the Library table where the date_created is greater than or equal to one_year_ago
    # The joinedload option is used to load the related LibraryName object at the same time as the Library object
    # This is done to avoid a separate database query when accessing the library attribute of the Library object
    # The query is limited to the first 10000 entries
    last_year = await db_ops.read_query(
        query=Select(Library).options(joinedload(Library.library)).where(and_(Library.date_created >= one_year_ago)),
        limit=10000,
    )

    # Create a Counter object from the library names in last_year
    # The Counter object counts the number of times each library name appears in last_year
    # This is done by iterating over each Library object in last_year and getting its library name
    library_counter = Counter(library.library.name for library in last_year)

    # Get the 10 most common library names
    # The most_common method of the Counter object returns a list of the n most common elements and their counts
    # In this case, it returns the 10 most common library names and their counts
    most_common_libraries = library_counter.most_common(10)

    # Return the list of the 10 most common library names and their counts
    return most_common_libraries

async def average_number_of_libraries_per_requirement():
    # Log the start of the function
    logger.info("Starting average_number_of_libraries_per_requirement")

    # Query the Library table for entries
    # This query will fetch the first 100,000 entries from the Library table
    logger.debug("Querying the Library table")
    lx = await db_ops.read_query(
        query=Select(Library)
        .limit(100000)
    )

    # Convert each Library object to a dictionary
    # This is done to make it easier to access the properties of each Library object
    logger.debug("Converting Library objects to dictionaries")
    libraries = [obj.__dict__ for obj in lx]

    # Group by request_group_id and count the number of libraries in each group
    # This is done by creating a dictionary where the keys are the request_group_ids and the values are the counts of libraries
    logger.debug("Grouping libraries by request_group_id")
    libraries_per_request_group = {}
    for library in libraries:
        request_group_id = library['request_group_id']
        if request_group_id in libraries_per_request_group:
            libraries_per_request_group[request_group_id] += 1
        else:
            libraries_per_request_group[request_group_id] = 1

    # Calculate the average number of libraries per request group
    # This is done by dividing the total number of libraries by the number of request groups
    # If there are no request groups, the average is set to 0
    logger.debug("Calculating the average number of libraries per request group")
    if len(libraries_per_request_group) == 0:
        average_number_of_libraries_per_request_group = 0
    else:
        average_number_of_libraries_per_request_group = round(sum(libraries_per_request_group.values()) / len(libraries_per_request_group), 1)

    # Log the calculated average
    logger.info(f"The average number of library requests per request group is {average_number_of_libraries_per_request_group}")

    # Return the calculated average
    return average_number_of_libraries_per_request_group


@router.get("/check")
async def get_check_form(request: Request, csrf_protect: CsrfProtect = Depends()):
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

    context = {
        "csrf_token": csrf_token,
        "request_group_id": str(uuid.uuid4()),
    }  # Use the generated CSRF token
    response = templates.TemplateResponse(
        request=request, name="pypi/new.html", context=context
    )
    csrf_protect.set_csrf_cookie(
        signed_token, response
    )  # Set the signed CSRF token in the cookie
    return response


@router.post("/check", response_class=RedirectResponse)
async def post_check_form(
    request: Request, request_group_id: str, csrf_protect: CsrfProtect = Depends()
):
    form = await request.form()
    # Validate the CSRF token
    await csrf_protect.validate_csrf(
        request
    )  # Pass the request object, not the csrf_token string
    # get form data from request

    # convert this to a list
    data = form["requirements"]
    data = data.split("\n")
    data = [x.strip() for x in data]
    data = [x for x in data if x != ""]
    # check packages
    pypi_response = await check_packages(
        packages=data, request_group_id=request_group_id, request=request
    )

    return RedirectResponse(url=f"/pypi/check/{request_group_id}", status_code=303)


@router.get("/check/{request_group_id}")
async def get_response(
    request: Request, request_group_id: str, csrf_protect: CsrfProtect = Depends()
):
    db_data = await db_ops.read_query(
        Select(Requirement).where(Requirement.request_group_id == request_group_id)
    )
    db_data_dict = [
        {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        for item in db_data
    ]

    context = {
        "data": db_data_dict,
        "request_group_id": request_group_id,
    }

    response = templates.TemplateResponse(request, "pypi/result.html", context=context)
    csrf_protect.unset_csrf_cookie(response)  # prevent token reuse
    return response


@router.get("/list")
async def get_all(request: Request):
    query = Select(Requirement)
    db_data = await db_ops.read_query(query=query, limit=100)
    count_data = await db_ops.count_query(query=query)

    db_data_dict = [
        {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        for item in db_data
    ]

    context = {
        "db_data": db_data_dict,
        "count_data": count_data,
    }

    return templates.TemplateResponse(request, "pypi/simple-list.html", context=context)
