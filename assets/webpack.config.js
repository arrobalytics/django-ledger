const path = require('path');

module.exports = {
    mode: "development",
    entry: {
        djetler: "./src/entry",
        styles: "./src/styles"
    },
    output: {
        filename: "[name].bundle.js",
        path: path.resolve(__dirname, '../django_ledger/static/django_ledger/bundle/'),
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
                    'style-loader',
                    'css-loader',
                ],
            },
            {
                test: /\.s[ac]ss$/i,
                use: [
                    'style-loader',
                    'css-loader',
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
            {
                test: /\.(png|woff|woff2|eot|ttf|svg)$/,
                use: {
                    loader: 'url-loader',
                    options: {
                        limit: 1000,
                        publicPath: '/static/django_ledger/bundle/files/',
                        outputPath: 'files/'
                    }
                },

            }
        ]
    }
};