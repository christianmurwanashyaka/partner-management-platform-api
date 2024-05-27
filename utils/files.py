import os
import tempfile
from datetime import datetime
from io import BytesIO
from itertools import chain

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt
from fastapi import UploadFile, HTTPException
from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from db.models import Activity, ActivityDomain, OperationalZone, InputDetail


async def handle_upload_file(file: UploadFile):
    upload_directory = os.path.join(os.getcwd(), 'uploads')
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


# async def generate_mou_doc(mou_application, template_path):
#     doc = Document(template_path)
#
#     organization = mou_application.mou_detail.project.organization
#     project = mou_application.mou_detail.project
#
#     # Collect unique domains from the project's activities
#     domains = set()
#     for activity in project.activities:
#         for activity_domain in activity.domains:
#             if activity_domain.domain_intervention:
#                 domains.add(activity_domain.domain_intervention.name)
#     domains_str = ', '.join(domains)
#
#     # Collect responsibilities and signatory details for the party with organization_id
#     responsibilities_str = ""
#     party_signatory = ""
#     party_position = "CEO"  # Default value
#     for party in mou_application.mou_detail.parties:
#         if party.organization_id:
#             responsibilities_str = "\n".join(
#                 [f"{idx + 1}. {responsibility}" for idx, responsibility in enumerate(party.responsibilities)])
#             party_signatory = party.signatory
#             print('PARTY SIGNATORY', party_signatory)
#             party_position = party.position
#             print('PARTY POSITION', party_position)
#
#     mappings = {
#         '{ORGANIZATION_NAME}': organization.name,
#         '{PROJECT_NAME}': project.name,
#         '{ORGANIZATION_PO_BOX}': organization.rwanda_po_box,
#         '{ORGANIZATION_PHONE}': organization.phone_number,
#         '{ORGANIZATION_EMAIL}': organization.email,
#         '{ORGANIZATION_WEBSITE}': organization.website,
#         '{ORGANIZATION_ADDRESS}': organization.rwanda_avenue,
#         '{OVERALL_GOAL}': project.goals[0].name if project.goals else '',
#         '{ACTIVITIES_DOMAINS}': domains_str,
#         '{PARTY_RESPONSIBILITIES}': responsibilities_str,
#         '{PARTY_SIGNATORY_NAME}': party_signatory,
#         '{PARTY_SIGNATORY_POSITION}': party_position
#     }
#
#     def replace_text(paragraph, mappings):
#         for key, value in mappings.items():
#             if key in paragraph.text:
#                 paragraph.text = paragraph.text.replace(key, str(value))
#
#     # Ensure the 'List Number' style exists
#     if 'List Number' not in [s.name for s in doc.styles]:
#         style = doc.styles.add_style('List Number', WD_STYLE_TYPE.PARAGRAPH)
#         style.base_style = doc.styles['Normal']
#         style.paragraph_format.left_indent = Pt(36)  # Set the left indentation
#         style.paragraph_format.space_before = Pt(0)
#         style.paragraph_format.space_after = Pt(0)
#         style.font.name = 'Times New Roman'
#         style.font.size = doc.styles['Normal'].font.size
#
#         # Set numbering for the style
#         p = style.element
#         num = OxmlElement('w:numPr')
#         ilvl = OxmlElement('w:ilvl')
#         ilvl.set(qn('w:val'), "0")
#         numId = OxmlElement('w:numId')
#         numId.set(qn('w:val'), "1")
#         num.append(ilvl)
#         num.append(numId)
#         p.append(num)
#
#     def set_font(paragraph, font_name='Times New Roman'):
#         for run in paragraph.runs:
#             run.font.name = font_name
#             run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
#
#     # Iterate through paragraphs to replace placeholders with actual values
#     for paragraph in doc.paragraphs:
#         replace_text(paragraph, mappings)
#
#         if '{PROJECT_GOALS}' in paragraph.text:
#             paragraph.text = paragraph.text.replace('{PROJECT_GOALS}', '')
#             for goal in project.goals:
#                 goal_paragraph = paragraph.insert_paragraph_before(goal.name)
#                 goal_paragraph.style = doc.styles['List Number']
#                 set_font(goal_paragraph)
#
#     # Save the modified document to a BytesIO object
#     buffer = BytesIO()
#     doc.save(buffer)
#     buffer.seek(0)
#     return buffer


async def generate_mou_doc(mou_application, template_path):
    doc = Document(template_path)

    organization = mou_application.mou_detail.project.organization
    project = mou_application.mou_detail.project

    # Collect unique domains from the project's activities
    domains = set()
    for activity in project.activities:
        for activity_domain in activity.domains:
            if activity_domain.domain_intervention:
                domains.add(activity_domain.domain_intervention.name)
    domains_str = ', '.join(domains)

    # Collect responsibilities and signatory details for the party with organization_id
    responsibilities_str = ""
    party_signatory = ""
    party_position = "CEO"  # Default value
    for party in mou_application.mou_detail.parties:
        if party.organization_id:
            responsibilities_str = "\n".join(
                [f"{idx + 1}. {responsibility}" for idx, responsibility in enumerate(party.responsibilities)])
            party_signatory = party.signatory
            party_position = party.position

    mappings = {
        '{ORGANIZATION_NAME}': organization.name,
        '{PROJECT_NAME}': project.name,
        '{ORGANIZATION_PO_BOX}': organization.rwanda_po_box,
        '{ORGANIZATION_PHONE}': organization.phone_number,
        '{ORGANIZATION_EMAIL}': organization.email,
        '{ORGANIZATION_WEBSITE}': organization.website,
        '{ORGANIZATION_ADDRESS}': organization.rwanda_avenue,
        '{OVERALL_GOAL}': project.goals[0].name if project.goals else '',
        '{ACTIVITIES_DOMAINS}': domains_str,
        '{PARTY_RESPONSIBILITIES}': responsibilities_str,
        '{PARTY_SIGNATORY_NAME}': party_signatory,
        '{PARTY_SIGNATORY_POSITION}': party_position
    }

    def replace_text(element, mappings):
        for key, value in mappings.items():
            if key in element.text:
                element.text = element.text.replace(key, str(value))

    # Iterate through all elements to replace placeholders
    for paragraph in doc.paragraphs:
        replace_text(paragraph, mappings)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_text(paragraph, mappings)

    for section in doc.sections:
        header = section.header
        footer = section.footer
        for paragraph in header.paragraphs:
            replace_text(paragraph, mappings)
        for paragraph in footer.paragraphs:
            replace_text(paragraph, mappings)

    if 'List Number' not in [s.name for s in doc.styles]:
        style = doc.styles.add_style('List Number', WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = doc.styles['Normal']
        style.paragraph_format.left_indent = Pt(36)  # Set the left indentation
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)
        style.font.name = 'Times New Roman'
        style.font.size = doc.styles['Normal'].font.size

        p = style.element
        num = OxmlElement('w:numPr')
        ilvl = OxmlElement('w:ilvl')
        ilvl.set(qn('w:val'), "0")
        numId = OxmlElement('w:numId')
        numId.set(qn('w:val'), "1")
        num.append(ilvl)
        num.append(numId)
        p.append(num)

    def set_font(paragraph, font_name='Times New Roman'):
        for run in paragraph.runs:
            run.font.name = font_name
            run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)

    for paragraph in doc.paragraphs:
        if '{PROJECT_GOALS}' in paragraph.text:
            paragraph.text = paragraph.text.replace('{PROJECT_GOALS}', '')
            for goal in project.goals:
                goal_paragraph = paragraph.insert_paragraph_before(goal.name)
                goal_paragraph.style = doc.styles['List Number']
                set_font(goal_paragraph)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


async def generate_mou_action_plan(mou_application, db: AsyncSession):
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

    # Fetching activities and their related data
    project_activities_query = select(Activity).where(Activity.project_id == project.uuid)
    activities = (await db.execute(project_activities_query)).scalars().all()

    for activity in activities:
        activity_domains_query = select(ActivityDomain).where(ActivityDomain.activity_id == activity.uuid)
        activity_domains = (await db.execute(activity_domains_query)).scalars().all()
        domain_names = ', '.join(set(domain.domain_intervention.name for domain in activity_domains))
        sub_domain_names = ', '.join(set(domain.sub_domain.name for domain in activity_domains))

        operational_zones_query = select(OperationalZone).where(OperationalZone.activity_id == activity.uuid)
        operational_zones = (await db.execute(operational_zones_query)).scalars().all()
        locations = set(zone.district + ', ' + zone.province for zone in operational_zones)

        input_details_query = select(InputDetail).where(InputDetail.activity_id == activity.uuid)
        input_details = (await db.execute(input_details_query)).scalars().all()
        input_categories = ', '.join(set(input_detail.input_category.name for input_detail in input_details))
        total_budget = sum(input_detail.budget for input_detail in input_details)
        input_names = ', '.join(f"{input_detail.input.name} - {input_detail.budget}" for input_detail in input_details)

        data = [
            organization.name,
            organization.organization_type.name,
            project.name,
            project.funding_source.name,
            project.funding_unit.name,
            activity.name,
            activity.description,
            project.budget_type.name,
            domain_names,
            sub_domain_names,
            activity.implementer,
            ', '.join(locations),
            input_categories,
            input_names,
            total_budget,
            project.currency,
            activity.fiscal_year
        ]
        ws.append(data)

    action_plans_directory = os.path.join(os.getcwd(), 'action_plans')
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
    directory = os.path.join(os.getcwd(), 'generated_mou_docs')
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, filename)
    with open(file_path, 'wb') as file:
        file.write(document_buffer.read())
    return file_path, filename
