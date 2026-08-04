"""``ModuleScaffolder`` — genera la estructura base de un módulo nuevo.

Sin CLI en este Sprint (ver "NO IMPLEMENTAR": generación de proyectos) — es
el servicio que una futura CLI invocará. ``scaffold()`` solo construye el
plan en memoria (``ModuleScaffold``); escribirlo a disco es un paso
explícito y separado (``write_to_disk``), nunca un efecto secundario
automático de generar el plan.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.sdk.templates import ModuleTemplate, get_template


@dataclass(frozen=True, slots=True)
class ModuleScaffold:
    """Plan de archivos de un módulo nuevo — rutas relativas a su contenido."""

    module_id: str
    files: Mapping[str, str]


class ModuleScaffolder:
    """Genera el esqueleto (sin código de negocio) de un módulo nuevo."""

    def scaffold(
        self, *, module_id: str, name: str, category: ModuleCategory = ModuleCategory.GENERIC
    ) -> ModuleScaffold:
        """Construye el plan de archivos para un módulo ``module_id`` de categoría ``category``."""
        template = get_template(category)
        files = {
            f"{module_id}/__init__.py": f'"""Módulo TEAF: {name}."""\n',
            f"{module_id}/module.py": self._render_module_file(
                module_id=module_id, name=name, template=template
            ),
            f"{module_id}/README.md": self._render_readme(
                module_id=module_id, name=name, template=template
            ),
        }
        return ModuleScaffold(module_id=module_id, files=files)

    def _render_module_file(self, *, module_id: str, name: str, template: ModuleTemplate) -> str:
        class_name = "".join(part.capitalize() for part in module_id.replace("-", "_").split("_"))
        capability_lines = "\n".join(
            f'            # .add_capability(id="{cap}", name="{cap}")'
            for cap in template.suggested_capabilities
        )
        service_lines = "\n".join(
            f"            # .add_service({service}, lambda c: ...)"
            for service in template.suggested_services
        )
        return (
            f'"""Módulo TEAF: {name} ({template.name}).\n\n'
            f'{template.description}\n"""\n\n'
            "from __future__ import annotations\n\n"
            "from backend.sdk.builder import ModuleBuilder\n"
            "from backend.sdk.context import ModuleContext\n"
            "from backend.sdk.manifest import ModuleManifest\n"
            "from backend.sdk.module_base import ModuleBase\n\n\n"
            f"class {class_name}Module(ModuleBase):\n"
            f'    """{name}."""\n\n'
            "    def get_manifest(self) -> ModuleManifest:\n"
            "        return (\n"
            f'            ModuleBuilder(id="{module_id}", name="{module_id}", '
            f'display_name="{name}")\n'
            f"{capability_lines}\n{service_lines}\n"
            "            .build()\n"
            "        )\n\n"
            "    # Sobrescribe los hooks que necesites: initialize, configure,\n"
            "    # register, start, ready, stop, dispose — todos opcionales.\n"
            "    async def ready(self, context: ModuleContext) -> None:\n"
            '        context.logger.info("module_ready")\n'
        )

    def _render_readme(self, *, module_id: str, name: str, template: ModuleTemplate) -> str:
        return (
            f"# {name}\n\n"
            f"{template.description}\n\n"
            f"Generado por `ModuleScaffolder` a partir de la plantilla "
            f"**{template.name}** (`{template.category.value}`).\n"
        )


def write_to_disk(scaffold: ModuleScaffold, base_path: Path) -> tuple[Path, ...]:
    """Materializa ``scaffold`` en disco, bajo ``base_path``. Devuelve las rutas escritas."""
    written: list[Path] = []
    for relative_path, content in scaffold.files.items():
        target = base_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return tuple(written)
