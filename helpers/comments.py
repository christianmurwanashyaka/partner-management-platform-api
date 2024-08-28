from typing import List

from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import UserRole, MOHStaffLevel, MouApplication
from schemas.mou_application import MouApplicationProjectRead


async def filter_comments_for_partner(db: AsyncSession, mou_applications: List[MouApplication]):
    filtered_applications = []

    for app in mou_applications:

        # Corrected filtering logic
        filtered_comments = [
            comment for comment in (app.comments or [])
            if comment.get('user', {}).get('level') == 'PARTNER_COORDINATOR'
        ]

        # Create a new instance with filtered comments
        filtered_app = MouApplicationProjectRead(
            uuid=app.uuid,
            reference_number=f"{app.created_at:%Y%m%d}-{app.uuid.int % 1000000:06d}",
            project_name=app.project_name,
            status=app.status,
            comments=filtered_comments,
            project_id=app.project_id,
            mou_detail_id=app.mou_detail_id,
            party_ids=app.party_ids,
            modification_entities=app.modification_entity
        )
        filtered_applications.append(filtered_app)

    return filtered_applications