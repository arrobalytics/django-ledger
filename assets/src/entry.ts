import Vue from 'vue';
import {DjetlerApp} from "./DjetlerApp";

let djetlerApp = new DjetlerApp();


let djetlerVueTest = new Vue({
    el: "#djetler-vue",
    delimiters: ["[[", "]]"],
    data: {
        message: "Hello Djetler!!!"
    }
});
