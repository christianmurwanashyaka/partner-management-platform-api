import os
import tempfile
from datetime import datetime
from io import BytesIO
from itertools import chain
from tempfile import NamedTemporaryFile

from docx2pdf import convert
from fastapi import status

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt
from fastapi import UploadFile, HTTPException, Depends
from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from db.database import get_db
from db.models import Activity, ActivityDomain, InputDetail, MouApplication, MouDetail, Project


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


async def generate_mou_doc(mou_application, template_path):
    doc = Document(template_path)

    organization = mou_application.mou_detail.project.organization
    project = mou_application.mou_detail.project
    current_date = datetime.now().strftime("%d/%m/%Y")

    def get_attr_or_none(obj, attr):
        value = getattr(obj, attr, None)
        return value if value != '' else None

    home_country = get_attr_or_none(organization, 'home_country')
    home_country_province = get_attr_or_none(organization, 'home_country_province')
    home_country_district = get_attr_or_none(organization, 'home_country_district')
    home_country_avenue = get_attr_or_none(organization, 'home_country_avenue')
    home_country_po_box = get_attr_or_none(organization, 'home_country_po_box')

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

    project_duration = project.duration if project.duration else "1"

    mappings = {
        '{ORGANIZATION_NAME}': organization.name,
        '{HOME_COUNTRY}': home_country,
        '{HOME_COUNTRY_PROVINCE}': home_country_province,
        '{HOME_COUNTRY_DISTRICT}': home_country_district,
        '{HOME_COUNTRY_AVENUE}': home_country_avenue,
        '{HOME_COUNTRY_PO_BOX}': home_country_po_box,
        '{PROJECT_NAME}': project.name,
        '{ORGANIZATION_PO_BOX}': organization.rwanda_po_box,
        '{ORGANIZATION_PHONE}': organization.phone_number,
        '{ORGANIZATION_EMAIL}': organization.email,
        '{ORGANIZATION_WEBSITE}': organization.website,
        '{ORGANIZATION_ADDRESS}': organization.rwanda_avenue,
        '{OVERALL_GOAL}': project.overall_goal,
        '{ACTIVITIES_DOMAINS}': domains_str,
        '{PARTY_RESPONSIBILITIES}': responsibilities_str,
        '{PARTY_SIGNATORY_NAME}': party_signatory,
        '{PARTY_SIGNATORY_POSITION}': party_position,
        '{DATE}': current_date,
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

    # buffer = BytesIO()
    # doc.save(buffer)
    # buffer.seek(0)
    # return buffer

    docx_buffer = BytesIO()
    doc.save(docx_buffer)
    docx_buffer.seek(0)

    pdf_buffer = BytesIO()

    with NamedTemporaryFile(delete=False, suffix='.docx') as tmp_docx:
        tmp_docx.write(docx_buffer.getvalue())
        tmp_docx_path = tmp_docx.name

    try:
        with NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
            tmp_pdf_path = tmp_pdf.name

        convert(tmp_docx_path, tmp_pdf_path)

        with open(tmp_pdf_path, 'rb') as pdf_file:
            pdf_buffer.write(pdf_file.read())
        pdf_buffer.seek(0)

    finally:
        os.unlink(tmp_docx_path)
        os.unlink(tmp_pdf_path)

    return docx_buffer, pdf_buffer


async def generate_mou_action_plan(mou_application, db: AsyncSession = Depends(get_db)):
    print('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX THIS IS IT XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
    wb = Workbook()
    ws = wb.active
    ws.title = 'Action Plan'
    print('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX AFTER TITLE XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')

    headers = [
        'Organization',
        'Organization Type',
        'Project Name',
        'Domain of Intervention',
        'Sub Domain of Intervention',
        'Sub Domain Function',
        'Sub Function',
        'Location',
        'Funding Source',
        'Funding Unit',
        'Activity',
        'Description of activity',
        'Input Category',
        'Inputs',
        'Planned budget',
        'Currency',
        'On/Off Budget/IGR',
        'Implementer',
        'Fiscal Year'
    ]
    ws.append(headers)

    bold_font = Font(bold=True)
    for cell in ws[1]:
        cell.font = bold_font
    print('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX BEFORE PROJECT XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
    query = select(MouApplication).options(
        selectinload(MouApplication.mou_detail).selectinload(MouDetail.project).selectinload(Project.organization)
    ).where(MouApplication.uuid == mou_application.uuid)

    result = await db.execute(query)
    mou_application = result.scalar_one_or_none()

    if not mou_application:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='MouApplication not found')

    project = mou_application.mou_detail.project
    organization = project.organization

    # project = await mou_application.mou_detail.project
    print('THE PROJECT :::::::::::::::::::', project)
    # organization = project.organization

    # Fetching activities and their related data
    project_activities_query = select(Activity).where(Activity.project_id == project.uuid)
    activities = (await db.execute(project_activities_query)).scalars().all()

    for activity in activities:
        activity_domains_query = select(ActivityDomain).where(ActivityDomain.activity_id == activity.uuid)
        activity_domains = (await db.execute(activity_domains_query)).scalars().all()

        input_details_query = select(InputDetail).where(InputDetail.activity_id == activity.uuid)
        input_details = (await db.execute(input_details_query)).scalars().all()

        for input_detail in input_details:
            location = f"{input_detail.district}, {input_detail.province}"
            input_category = input_detail.input_category.name
            input_name = input_detail.input.name
            budget = input_detail.budget

            for domain in activity_domains:
                domain_name = domain.domain_intervention.name
                sub_domain_name = domain.sub_domain.name
                sub_domain_function_name = domain.sub_domain_function.name if domain.sub_domain_function else "N/A"
                sub_function_name = domain.sub_function.name if domain.sub_function else "N/A"

                data = [
                    organization.name,
                    organization.organization_type.name,
                    project.name,
                    domain_name,
                    sub_domain_name,
                    sub_domain_function_name,
                    sub_function_name,
                    location,
                    project.funding_source.name,
                    project.funding_unit.name,
                    activity.name,
                    activity.description,
                    input_category,
                    input_name,
                    budget,
                    project.currency,
                    project.budget_type.name,
                    activity.implementer,
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


async def save_mou_doc_to_disk(document_buffer, filename, doc_type):
    directory = os.path.join(os.getcwd(), f'generated_mou_docs_{doc_type}')
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, filename)
    with open(file_path, 'wb') as file:
        file.write(document_buffer.getvalue())  # Use getvalue() instead of read()
    return file_path, filename
