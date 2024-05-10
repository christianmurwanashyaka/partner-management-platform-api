import os
from datetime import datetime
from io import BytesIO
from itertools import chain

from docx import Document
from fastapi import UploadFile, HTTPException
from openpyxl import Workbook
from openpyxl.styles import Font


async def handle_upload_file(file: UploadFile):
    upload_directory = 'uploads'
    os.makedirs(upload_directory, exist_ok=True)

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{timestamp}_{file.filename}'
        file_path = os.path.join(upload_directory, filename)

        with open(file_path, 'wb+') as file_object:
            file_object.write(await file.read())

        return file_path, filename
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


# async def generate_mou_action_plan(mou_application):
#     wb = Workbook()
#     ws = wb.active
#     ws.title = 'Action Plan'
#
#     headers = [
#         'Organization',
#         'Organization type',
#         'Project name',
#         'Funding source',
#         'Funding unit',
#         'Activity',
#         'Description of activity',
#         'On/Off Budget/IGR',
#         'Domain of intervention',
#         'Sub domain of intervention',
#         'Implementer',
#         'Location',
#         'Input category',
#         'Inputs',
#         'Planned budget',
#         'Currency',
#         'Fiscal Year'
#     ]
#     ws.append(headers)
#
#     bold_font = Font(bold=True)
#     for cell in ws[1]:
#         cell.font = bold_font
#
#     project = mou_application.mou_detail.project
#     organization = project.organization
#
#     for activity in project.activities:
#         for input_detail in activity.input_details:
#             input_name = f"{input_detail.input.name} - {input_detail.budget}"
#             input_categories = ', '.join(set(input_detail.input_category.name for input_detail in activity.input_details))
#             total_budget = sum(input_detail.budget for input_detail in activity.input_details)
#             # Flatten and deduplicate all districts and provinces
#             locations = set(chain.from_iterable(input_detail.districts + input_detail.provinces for input_detail in activity.input_details))
#
#             data = [
#                 organization.name,
#                 organization.organization_type.name,
#                 project.name,
#                 project.funding_source.name,
#                 project.funding_unit.name,
#                 activity.name,
#                 activity.description,
#                 project.budget_type.name,
#                 project.domain_intervention.name,
#                 activity.sub_domain.name,
#                 activity.implementer,
#                 ', '.join(locations),
#                 input_categories,
#                 input_name,
#                 total_budget,
#                 project.currency,
#                 activity.fiscal_year
#             ]
#             ws.append(data)
#
#     action_plans_directory = 'action_plans'
#     os.makedirs(action_plans_directory, exist_ok=True)
#     try:
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         filename = f'{timestamp}_action_plan_{mou_application.created_by}.xlsx'
#         file_path = os.path.join(action_plans_directory, filename)
#
#         wb.save(file_path)
#         return file_path, filename
#     except Exception as e:
#         raise Exception(f"Failed to save file: {str(e)}")


async def generate_mou_doc(mou_application, template_path):
    doc = Document(template_path)

    organization = mou_application.mou_detail.project.organization
    project = mou_application.mou_detail.project

    mappings = {
        '{ORGANIZATION_NAME}': organization.name,
        '{PROJECT_NAME}': project.name,
        '{ORGANIZATION_PO_BOX}': organization.rwanda_po_box,
        '{ORGANIZATION_PHONE}': organization.phone_number,
        '{ORGANIZATION_EMAIL}': organization.email,
        '{ORGANIZATION_WEBSITE}': organization.website,
        '{ORGANIZATION_ADDRESS}': organization.rwanda_avenue
    }

    for paragraph in doc.paragraphs:
        for key, value in mappings.items():
            if value:
                paragraph.text = paragraph.text.replace(key, value)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


async def generate_mou_action_plan(mou_application):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Action Plan'

    headers = [
        'Organization',
        'Organization type',
        'Project name',
        'Funding source',
        'Funding unit',
        'Activity',
        'Description of activity',
        'On/Off Budget/IGR',
        'Domain of intervention',
        'Sub domain of intervention',
        'Implementer',
        'Location',
        'Input category',
        'Inputs',
        'Planned budget',
        'Currency',
        'Fiscal Year'
    ]
    ws.append(headers)

    bold_font = Font(bold=True)
    for cell in ws[1]:
        cell.font = bold_font

    project = mou_application.mou_detail.project
    organization = project.organization

    for activity in project.activities:
        for input_detail in activity.input_details:
            input_name = f"{input_detail.input.name} - {input_detail.budget}"
            input_categories = ', '.join(set(input_detail.input_category.name for input_detail in activity.input_details))
            total_budget = sum(input_detail.budget for input_detail in activity.input_details)
            # Flatten and deduplicate all districts and provinces
            locations = set(input_detail.district + ', ' + input_detail.province for input_detail in activity.input_details)

            data = [
                organization.name,
                organization.organization_type.name,
                project.name,
                project.funding_source.name,
                project.funding_unit.name,
                activity.name,
                activity.description,
                project.budget_type.name,
                project.domain_intervention.name,
                activity.sub_domain.name,
                activity.implementer,
                ', '.join(locations),
                input_categories,
                input_name,
                total_budget,
                project.currency,
                activity.fiscal_year
            ]
            ws.append(data)

    action_plans_directory = 'action_plans'
    os.makedirs(action_plans_directory, exist_ok=True)
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{timestamp}_action_plan_{mou_application.created_by}.xlsx'
        file_path = os.path.join(action_plans_directory, filename)

        wb.save(file_path)
        return file_path, filename
    except Exception as e:
        raise Exception(f"Failed to save file: {str(e)}")


async def save_mou_doc_to_disk(document_buffer, filename):
    file_path = os.path.join('generated_mou_docs', filename)
    with open(file_path, 'wb') as file:
        file.write(document_buffer.read())
    return file_path, filename
