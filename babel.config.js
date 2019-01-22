module.exports = function (api) {
  api.cache(true);

  const presets = [
    ['@babel/preset-env', {
      useBuiltIns: 'entry'
    }]
  ];
  const plugins = [
    '@babel/plugin-proposal-object-rest-spread',
    '@babel/plugin-proposal-class-properties'
  ];

  return {
    presets,
    plugins
  };
};
