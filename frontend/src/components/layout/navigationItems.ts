/**
 * Elementos de la navegación principal.
 *
 * Viven fuera del componente para que la barra lateral y las pruebas de
 * navegación lean la misma lista: una ruta añadida aquí aparece en el menú sin
 * tocar JSX, y una prueba puede recorrerla sin duplicarla.
 *
 * Cada entrada corresponde a una capacidad **real** del backend TEAF
 * (ver `hooks/queries/useSystem.ts`); no hay entradas de módulos de negocio,
 * que pertenecen a las aplicaciones construidas sobre el framework y no al
 * framework (CLAUDE.md §1).
 */
export interface NavigationItem {
  label: string;
  path: string;
  /** Texto de apoyo para lectores de pantalla y tooltips. */
  description: string;
}

export const navigationItems: readonly NavigationItem[] = [
  {
    label: 'Panel',
    path: '/',
    description: 'Estado general de la instancia',
  },
  {
    label: 'Módulos',
    path: '/modules',
    description: 'Módulos registrados en el Runtime',
  },
  {
    label: 'Eventos',
    path: '/events',
    description: 'Historial del EventBus del Runtime',
  },
  {
    label: 'Runtime',
    path: '/runtime',
    description: 'Servicios, capacidades, feature flags y plugins',
  },
] as const;
