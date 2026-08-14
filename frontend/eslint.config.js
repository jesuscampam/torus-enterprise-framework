import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'coverage', 'node_modules'] },
  js.configs.recommended,
  // `recommendedTypeChecked` usa el type checker: detecta promesas sin await,
  // accesos inseguros a `any` y comparaciones imposibles — la clase de fallo
  // que las reglas puramente sintácticas no ven.
  ...tseslint.configs.recommendedTypeChecked,
  // `configs.flat` es la variante en formato flat config; `configs['recommended-latest']`
  // sigue el formato eslintrc antiguo y ESLint 10 lo rechaza.
  reactHooks.configs.flat['recommended-latest'],
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    // Los ficheros de configuración corren en Node, no en el navegador, y
    // quedan fuera del `tsconfig.json` de la aplicación.
    files: ['*.config.{js,ts}'],
    languageOptions: { globals: globals.node },
    ...tseslint.configs.disableTypeChecked,
  }
);
