"""``ModuleDocumentationGenerator`` — genera documentación Markdown de un módulo.

Solo el servicio en este Sprint (ver Sprint 2.5, ítem 14): ``generate()``
devuelve un ``str`` — nada escribe a disco. Un Sprint futuro (o la CLI
todavía no implementada) decide dónde y cuándo persistir el resultado.
"""

from __future__ import annotations

from teaf._internal.sdk.manifest import ModuleManifest


class ModuleDocumentationGenerator:
    """Genera un documento Markdown a partir de un ``ModuleManifest``."""

    def generate(self, manifest: ModuleManifest) -> str:
        """Construye la documentación completa del módulo descrito por ``manifest``."""
        sections = [
            self._render_header(manifest),
            self._render_capabilities(manifest),
            self._render_services(manifest),
            self._render_dependencies(manifest),
            self._render_configuration(manifest),
            self._render_health(manifest),
            self._render_events(manifest),
            self._render_compatibility(manifest),
        ]
        return "\n".join(section for section in sections if section)

    def _render_header(self, manifest: ModuleManifest) -> str:
        descriptor = manifest.descriptor
        lines = [f"# {descriptor.display_name}", ""]
        if descriptor.description:
            lines.append(descriptor.description)
            lines.append("")
        lines.append(f"- **Id**: `{descriptor.id}`")
        lines.append(f"- **Versión**: `{descriptor.version}`")
        lines.append(f"- **Categoría**: `{descriptor.category.value}`")
        if descriptor.author:
            lines.append(f"- **Autor**: {descriptor.author}")
        if manifest.license:
            lines.append(f"- **Licencia**: {manifest.license}")
        if descriptor.tags:
            lines.append(f"- **Tags**: {', '.join(descriptor.tags)}")
        if descriptor.experimental:
            lines.append("- **Experimental**: sí")
        if descriptor.deprecated:
            lines.append("- **Deprecado**: sí")
        if descriptor.documentation:
            lines.append(f"- **Documentación**: {descriptor.documentation}")
        lines.append("")
        return "\n".join(lines)

    def _render_capabilities(self, manifest: ModuleManifest) -> str:
        if not manifest.capabilities:
            return ""
        lines = [
            "## Capacidades",
            "",
            "| Id | Nombre | Categoría | Descripción |",
            "|---|---|---|---|",
        ]
        for capability in manifest.capabilities:
            lines.append(
                f"| `{capability.id}` | {capability.name} | {capability.category.value} "
                f"| {capability.description} |"
            )
        lines.append("")
        return "\n".join(lines)

    def _render_services(self, manifest: ModuleManifest) -> str:
        if not manifest.services:
            return ""
        lines = ["## Servicios", "", "| Contrato | Lifetime | Descripción |", "|---|---|---|"]
        for service in manifest.services:
            lines.append(
                f"| `{service.contract.__name__}` | {service.lifetime.value} "
                f"| {service.description} |"
            )
        lines.append("")
        return "\n".join(lines)

    def _render_dependencies(self, manifest: ModuleManifest) -> str:
        if not manifest.dependencies:
            return ""
        lines = ["## Dependencias", "", "| Módulo | Versión | Opcional |", "|---|---|---|"]
        for dependency in manifest.dependencies:
            lines.append(
                f"| `{dependency.module_id}` | {dependency.version_constraint or '*'} "
                f"| {'sí' if dependency.optional else 'no'} |"
            )
        lines.append("")
        return "\n".join(lines)

    def _render_configuration(self, manifest: ModuleManifest) -> str:
        if not manifest.configuration:
            return ""
        lines = [
            "## Configuración",
            "",
            "| Clave | Requerida | Sensible | Descripción |",
            "|---|---|---|---|",
        ]
        for entry in manifest.configuration:
            lines.append(
                f"| `{entry.key}` | {'sí' if entry.required else 'no'} "
                f"| {'sí' if entry.sensitive else 'no'} | {entry.description} |"
            )
        lines.append("")
        return "\n".join(lines)

    def _render_health(self, manifest: ModuleManifest) -> str:
        if not manifest.health_checks:
            return ""
        lines = ["## Health Checks", "", "| Nombre | Descripción |", "|---|---|"]
        for health_check in manifest.health_checks:
            lines.append(f"| `{health_check.name}` | {health_check.description} |")
        lines.append("")
        return "\n".join(lines)

    def _render_events(self, manifest: ModuleManifest) -> str:
        if not manifest.events:
            return ""
        lines = ["## Eventos", ""]
        lines.extend(f"- `{event}`" for event in manifest.events)
        lines.append("")
        return "\n".join(lines)

    def _render_compatibility(self, manifest: ModuleManifest) -> str:
        lines = [
            "## Compatibilidad",
            "",
            f"- **Runtime**: `{manifest.runtime_compatibility}`",
            f"- **SDK**: `{manifest.sdk_compatibility}`",
            "",
        ]
        return "\n".join(lines)
