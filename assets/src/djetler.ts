import {Vue} from "vue/types/vue";

let vueComp = Vue.component("test",{
    data: {
        message: "Test component!!!"
    },
});

let djetler = new Vue({
    el: "#djetler-vue",
    data: {
        message: "You did it!!!"
    }
});

// Dismiss Notifications
// document.addEventListener('DOMContentLoaded', () => {
//     (document.querySelectorAll('.notification .delete') || []).forEach(($delete) => {
//         $notification = $delete.parentNode;
//         $delete.addEventListener('click', () => {
//             $notification.parentNode.removeChild($notification);
//         });
//     });
// });
//
// // Navbar burger button
// document.addEventListener('DOMContentLoaded', () => {
//
//     // Get all "navbar-burger" elements
//     const $navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);
//
//     // Check if there are any navbar burgers
//     if ($navbarBurgers.length > 0) {
//
//         // Add a click event on each of them
//         $navbarBurgers.forEach(el => {
//             el.addEventListener('click', () => {
//
//                 // Get the target from the "data-target" attribute
//                 const target = el.dataset.target;
//                 const $target = document.getElementById(target);
//
//                 // Toggle the "is-active" class on both the "navbar-burger" and the "navbar-menu"
//                 el.classList.toggle('is-active');
//                 $target.classList.toggle('is-active');
//
//             });
//         });
//     }
//
// });
