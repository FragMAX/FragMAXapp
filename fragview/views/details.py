#
# project details for PDB deposition
#
from typing import List, Dict
import json
import jsonschema
from json import JSONDecodeError
from jsonschema import ValidationError
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.http.request import HttpRequest
from fragview import pdbx
from fragview.projects import Project, current_project

SCIENTIST_SCHEMA = {
    "type": "object",
    "properties": {
        "ORCID": {"type": "string"},
        "Salutation": {"type": "string"},
        "FirstName": {"type": "string"},
        "LastName": {"type": "string"},
        "Role": {"type": "string"},
        "OrganizationType": {"type": "string"},
        "OrganizationName": {"type": "string"},
        "Street": {"type": "string"},
        "City": {"type": "string"},
        "ZIPCode": {"type": "string"},
        "Country": {"type": "string"},
        "Email": {"type": "string"},
        "Phone": {"type": "string"},
    },
}

AUTHOR_SCHEMA = {
    "type": "object",
    "properties": {
        "Name": {"type": "string"},
        "ORCID": {"type": "string"},
    },
}

ENTITIES_SCHEMA = {
    "type": "object",
    "properties": {
        "UniprotID": {"type": "string"},
        "Sequence": {"type": "string"},
    },
}

FUNDING_SCHEMA = {
    "type": "object",
    "properties": {
        "Organization": {"type": "string"},
        "GrantNumber": {"type": "string"},
    },
}

DETAILS_SCHEMA = {
    "type": "object",
    "properties": {
        "PrincipalInvestigator": SCIENTIST_SCHEMA,
        "ResponsibleScientists": {
            "type": "array",
            "items": SCIENTIST_SCHEMA,
        },
        "Authors": {
            "type": "array",
            "items": AUTHOR_SCHEMA,
        },
        "Entities": {
            "type": "array",
            "items": ENTITIES_SCHEMA,
        },
        "Funding": {
            "type": "array",
            "items": FUNDING_SCHEMA,
        },
        "SequenceRelease": {"type": "string"},
        "CoordinatesRelease": {"type": "string"},
        "DepositionTitle": {"type": "string"},
        "Description": {"type": "string"},
        "Keywords": {"type": "string"},
        "BiologicalAssembly": {"type": "string"},
        "StructureTitle": {"type": "string"},
        "DepositPandda": {"type": "boolean"},
        "ApoStructureTitle": {"type": "string"},
    },
    "required": ["PrincipalInvestigator"],
}


def ui(request: HttpRequest):
    return render(
        request,
        "details.html",
        {
            "salutations": pdbx.SALUTATIONS,
            "roles": pdbx.ROLES,
            "organization_types": pdbx.ORGANIZATION_TYPES,
            "countries": pdbx.COUNTRIES,
            "sequence_release": pdbx.SEQUENCE_RELEASE,
            "coordinates_release": pdbx.COORDINATES_RELEASE,
            "funding_organizations": pdbx.FUNDING_ORGANIZATIONS,
        },
    )


def _scientist_db_to_dict(scientist) -> Dict:
    if scientist is None:
        return {}

    return {
        "ORCID": scientist.orcid,
        "Salutation": scientist.salutation,
        "FirstName": scientist.first_name,
        "LastName": scientist.last_name,
        "Role": scientist.role,
        "OrganizationType": scientist.organization_type,
        "OrganizationName": scientist.organization_name,
        "Street": scientist.street,
        "City": scientist.city,
        "ZIPCode": scientist.zip_code,
        "Country": scientist.country,
        "Email": scientist.email,
        "Phone": scientist.phone,
    }


def _load_responsible_scientists(project: Project):
    for scientist in project.get_scientists():
        if scientist == project.details.principal_investigator:
            # don't include principal investigator entry
            continue

        yield _scientist_db_to_dict(scientist)


def _load_authors(project: Project):
    for author in project.db.Author.select():
        yield {
            "Name": author.name,
            "ORCID": author.orcid,
        }


def _load_entities(project: Project):
    for entity in project.db.ProteinEntity.select():
        yield {
            "UniprotID": entity.uniprot_id,
            "Sequence": entity.sequence,
        }


def _load_funding(project: Project):
    for forg in project.db.Funding.select():
        yield {
            "Organization": forg.organization,
            "GrantNumber": forg.grant_number,
        }


def _load_details(project: Project) -> JsonResponse:
    details = project.details
    return JsonResponse(
        {
            "PrincipalInvestigator": _scientist_db_to_dict(
                details.principal_investigator
            ),
            "ResponsibleScientists": list(_load_responsible_scientists(project)),
            "Authors": list(_load_authors(project)),
            "Entities": list(_load_entities(project)),
            "Funding": list(_load_funding(project)),
            "SequenceRelease": details.sequence_release,
            "CoordinatesRelease": details.coordinates_release,
            "DepositionTitle": details.deposition_title,
            "Description": details.description,
            "Keywords": details.keywords,
            "BiologicalAssembly": details.biological_assembly,
            "StructureTitle": details.structure_title,
            "DepositPandda": details.deposit_pandda,
            "ApoStructureTitle": details.apo_structure_title,
            "StartingModel": details.starting_model,
        }
    )


def _save_scientists(
    project: Project,
    principal_investigator: Dict,
    responsible_scientists: List[Dict],
):
    def save_scientist(scientist: Dict):
        return project.db.Scientist(
            orcid=scientist.get("ORCID", ""),
            salutation=scientist.get("Salutation", ""),
            first_name=scientist.get("FirstName", ""),
            last_name=scientist.get("LastName", ""),
            role=scientist.get("Role", ""),
            organization_type=scientist.get("OrganizationType", ""),
            organization_name=scientist.get("OrganizationName", ""),
            street=scientist.get("Street", ""),
            city=scientist.get("City", ""),
            zip_code=scientist.get("ZIPCode", ""),
            country=scientist.get("Country", ""),
            email=scientist.get("Email", ""),
            phone=scientist.get("Phone", ""),
        )

    # delete all scientist entries from the database
    for scientist in project.get_scientists():
        scientist.delete()

    project.details.principal_investigator = save_scientist(principal_investigator)

    for scientist in responsible_scientists:
        save_scientist(scientist)


def _save_authors(project: Project, authors: List[Dict]):
    for author in project.db.Author.select():
        author.delete()

    for author in authors:
        project.db.Author(
            orcid=author.get("ORCID", ""),
            name=author.get("Name", ""),
        )


def _save_entities(project: Project, entities: List[Dict]):
    for entity in project.db.ProteinEntity.select():
        entity.delete()

    for entity in entities:
        project.db.ProteinEntity(
            uniprot_id=entity.get("UniprotID", ""),
            sequence=entity.get("Sequence", ""),
        )


def _save_funding(project: Project, funding: List[Dict]):
    for forg in project.db.Funding.select():
        forg.delete()

    for forg in funding:
        project.db.Funding(
            organization=forg.get("Organization", ""),
            grant_number=forg.get("GrantNumber", ""),
        )


def _save_details(project: Project, post):
    details = post.get("details")

    if details is None:
        return HttpResponseBadRequest(f"missing 'details' form field")

    try:
        details = json.loads(post["details"])
    except JSONDecodeError as ex:
        return HttpResponseBadRequest(f"could not parse json:\n{ex}")

    try:
        jsonschema.validate(details, DETAILS_SCHEMA)
    except ValidationError as ex:
        return HttpResponseBadRequest(f"data validate schema:\n{ex}")

    _save_scientists(
        project, details["PrincipalInvestigator"], details["ResponsibleScientists"]
    )
    _save_authors(project, details["Authors"])
    _save_entities(project, details["Entities"])
    _save_funding(project, details["Funding"])

    db_details = project.details
    db_details.sequence_release = details["SequenceRelease"]
    db_details.coordinates_release = details["CoordinatesRelease"]
    db_details.deposition_title = details["DepositionTitle"]
    db_details.description = details["Description"]
    db_details.keywords = details["Keywords"]
    db_details.biological_assembly = details["BiologicalAssembly"]
    db_details.structure_title = details["StructureTitle"]
    db_details.deposit_pandda = details["DepositPandda"]
    db_details.apo_structure_title = details["ApoStructureTitle"]
    db_details.starting_model = details["StartingModel"]

    return HttpResponse("ok")


def details(request: HttpRequest):
    project = current_project(request)
    if request.method == "GET":
        return _load_details(project)

    assert request.method == "POST"
    return _save_details(project, request.POST)


def dump_details(request: HttpRequest, project_id):
    from fragview.projects import get_project

    proj = get_project(project_id)
    return _load_details(proj)
