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
        library: "djLedger",
        // libraryTarget: "umd"
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
                test: /\.less$/,
                use: [
                    {
                        loader: 'style-loader',
                    },
                    {
                        loader: 'css-loader',
                    },
                    {
                        loader: 'less-loader',
                        options: {
                            lessOptions: {
                                strictMath: true,
                            },
                        },
                    },
                ],
            },
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
        ]
    }
};