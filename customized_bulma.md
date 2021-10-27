###Bulma is highly customizable thanks to 419 Sass variables living across 28 files.

node and npm version used:
- npm v6.14.x
- node v10.19.x

####For customizing

first make sure that you are in assets directory.
####installing packages from package.json
```shell script
npm install
```

####customization in bulma open
```shell script
assets/src/djetler.scss
```

For bulma variables visit bulma documentation

```shell script
https://bulma.io/documentation/customize/variables/
```
####example 
variable for changing menu background color on hover

```shell script
$menu-item-hover-background-color: #000000 !default
```

####In order to reflect the changes into frontend, run

```shell script
npm run build
```
