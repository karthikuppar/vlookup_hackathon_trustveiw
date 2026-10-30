module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } },
  settings: { react: { version: '18.2' } },
  extends: ['eslint:recommended', 'plugin:react/recommended', 'plugin:react/jsx-runtime', 'plugin:react-hooks/recommended'],
  plugins: ['react', 'react-hooks'],
  ignorePatterns: ['dist', 'node_modules', 'public', '*.config.js'],
  rules: {
    // Project does not use PropTypes.
    'react/prop-types': 'off',
    'react/no-unescaped-entities': 'off',
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^(_|React$)' }],
  },
  overrides: [
    {
      // Legacy offline-engine code carried over from an earlier project; unused
      // helpers there are harmless and not worth churning. no-undef stays on.
      files: ['src/utils/**', 'src/services/api.js'],
      rules: { 'no-unused-vars': 'off' },
    },
  ],
}
