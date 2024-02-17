# -*- coding: utf-8 -*-

import uuid
from datetime import datetime, timedelta

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


async def most_common_library():
    # Calculate the date one year ago from now
    one_year_ago = datetime.now() - timedelta(days=365)

    # Query the Library table for entries from the last year
    last_year = await db_ops.read_query(
        query=Select(Library).where(and_(Library.date_created >= one_year_ago)),
        limit=10000,
    )
    # count the number of times each library id appears in last_year and return the top 10


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
    average_number_of_libraries_per_request_group = await db_ops.read_query(
        query=Select(
            Library.request_group_id, func.count(Library.library_id).label("count")
        ).group_by(Library.request_group_id)
    )
    print(type(average_number_of_libraries_per_request_group))
    # Calculate the average
    if len(average_number_of_libraries_per_request_group) == 0:
        average_number_of_libraries_per_requirement = 0
    else:
        average_number_of_libraries_per_requirement = sum(
            [int(group[1]) for group in average_number_of_libraries_per_request_group]
        ) / len(average_number_of_libraries_per_request_group)

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
        "average_number_of_libraries_per_requirement": average_number_of_libraries_per_requirement,
        "total_number_of_vulnerabilities": total_number_of_vulnerabilities,
        # "most_common_libraries": most_common_libraries,
        "libraries_with_most_vulnerabilities": libraries_with_most_vulnerabilities,
        "last_one_hundred_requests": last_one_hundred_requests,
        "library_name": library_name,
    }
    return templates.TemplateResponse(
        request=request, name="/pypi/dashboard.html", context=context
    )


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


# from fastapi import FastAPI

# app = FastAPI()
# @app.exception_handler(CsrfProtectError)
# def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
#     return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
