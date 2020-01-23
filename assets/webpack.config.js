const path = require('path');

module.exports = {
    mode: "development",
    entry: {
        djetler: "./src/entry",
        styles: "./src/styles"
    },
    output: {
        filename: "[name].bundle.js",
        path: path.resolve(__dirname, '../django_ledger/static/django_ledger/dist/')
    },
    resolve: {
        extensions: [".ts", ".tsx", ".js"],
        modules: ["node_modules"],
        alias: {
            vue: 'vue/dist/vue.js'
        },
    },
    module: {
        rules: [
            {
                test: /\.css$/i,
                use: [
                    'style-loader', 'css-loader'
                ],
            },
            {
                test: /\.s[ac]ss$/i,
                use: [
                    // Creates `style` nodes from JS strings
                    'style-loader',
                    // Translates CSS into CommonJS
                    'css-loader',
                    // Compiles Sass to CSS
                    'sass-loader',
                ],
            },
            {
                test: /\.tsx?$/,
                use: [
                    "ts-loader"
                ],
            },
            {
                test: /\.less$/,
                use: [
                    "less-loader"
                ],
            },
        ]
    }
};