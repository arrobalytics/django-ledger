import Vue from 'vue';
import {DjetlerApp} from "./DjetlerApp";

// console.log(mdiAccount);

new DjetlerApp();

let djetlerVueTest = new Vue({
    el: "#djetler-vue",
    delimiters: ["[[", "]]"],
    data: {
        message: "Hello Djetler!!!"
    }
});
