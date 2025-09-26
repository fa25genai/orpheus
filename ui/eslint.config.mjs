import js from "@eslint/js";
import nextPlugin from "@next/eslint-plugin-next";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import unusedImports from "eslint-plugin-unused-imports";
import globals from "globals";

export default [
  // Base JS recommendations
  js.configs.recommended,
  // Next.js flat configs (recommended + Core Web Vitals)
  nextPlugin.flatConfig.recommended,
  nextPlugin.flatConfig.coreWebVitals,
  // Apply TypeScript recommended (flat) without type-checking requirement
  ...tsPlugin.configs["flat/recommended"],
  // Globals and project-specific rules
  {
    files: ["**/*.{ts,tsx}", "**/*.js"],
    languageOptions: {
      parser: tsParser,
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      "unused-imports": unusedImports,
    },
    rules: {
      // Remove unused imports and flag unused vars (allow leading underscore)
      "unused-imports/no-unused-imports": "error",
      "unused-imports/no-unused-vars": [
        "warn",
        {
          args: "after-used",
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          ignoreRestSiblings: true,
        },
      ],
    },
  },
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
      "generated-api-clients/**",
    ],
  },
];
