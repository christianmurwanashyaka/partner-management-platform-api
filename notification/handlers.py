from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

from core.config import settings


class TemplateHandler:
    def __init__(self):
        template_dir = Path(__file__).parent
        # Verify the directory exists
        if not template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    async def render_template(self, template_name: str, **kwargs) -> str:
        try:
            template = self.env.get_template(f"emails/{template_name}")
            kwargs['year'] = datetime.now().year
            rendered_content = template.render(
                **kwargs,
                system_name=settings.SYSTEM_NAME
            )
            return rendered_content
        except Exception as e:
            import traceback
            raise