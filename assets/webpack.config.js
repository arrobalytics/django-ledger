const path = require('path');

module.exports = {
    mode: "development",
    entry: "./src/djetler.ts",
    output: {
        path: path.resolve('./dist'),
        filename: "djetler.bundle.js"
    },
    resolve: {
        extensions: [".ts", ".tsx", ".js"],
        modules: [
            "node_modules",
            // path.resolve(__dirname, "node_modules")
        ]
    },
    module: {
        rules: [
            {
                test: /\.css$/i,
                use: ['style-loader', 'css-loader'],
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
                loader: "ts-loader",
                exclude: "/node_modules/"
            }
        ]
    }
};