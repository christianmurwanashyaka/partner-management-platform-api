import os
from datetime import datetime
from io import BytesIO

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

    project_activities = project.activities

    for idx, activity in enumerate(project_activities, start=2):
        input_details = []
        for input_detail in activity.input_details:
            input_details.append(f"{input_detail.input.name} - {input_detail.budget}")

        input_names = ', '.join(input_details)

        if idx == 2:
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
               ', '.join(activity.districts),
               ', '.join(set(input_detail.input_category.name for input_detail in activity.input_details)),
               input_names,
               sum(input_detail.budget for input_detail in activity.input_details),
               'RWF',
               activity.fiscal_year
           ]
        else:
            data = [
                '',
                '',
                '',
                '',
                '',
                activity.name,
                activity.description,
                '',
                '',
                activity.sub_domain.name,
                activity.implementer,
                ', '.join(activity.districts),
                ', '.join(set(input_detail.input_category.name for input_detail in activity.input_details)),
                input_names,
                sum(input_detail.budget for input_detail in activity.input_details),
                'RWF',
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
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
