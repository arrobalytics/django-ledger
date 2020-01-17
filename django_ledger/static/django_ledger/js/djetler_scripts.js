// Dismiss Notifications
document.addEventListener('DOMContentLoaded', () => {
    (document.querySelectorAll('.notification .delete') || []).forEach(($delete) => {
        $notification = $delete.parentNode;
        $delete.addEventListener('click', () => {
            $notification.parentNode.removeChild($notification);
        });
    });
});

// Navbar burger button
document.addEventListener('DOMContentLoaded', () => {

    // Get all "navbar-burger" elements
    const $navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);

    // Check if there are any navbar burgers
    if ($navbarBurgers.length > 0) {

        // Add a click event on each of them
        $navbarBurgers.forEach(el => {
            el.addEventListener('click', () => {

                // Get the target from the "data-target" attribute
                const target = el.dataset.target;
                const $target = document.getElementById(target);

                // Toggle the "is-active" class on both the "navbar-burger" and the "navbar-menu"
                el.classList.toggle('is-active');
                $target.classList.toggle('is-active');

            });
        });
    }

});

// Change entity from Nav
function setDefaultEntity() {
    let defaultEntityForm = document.getElementById("djetler-set-entity-form");
    defaultEntityForm.submit();
}


// Entity Date Filter
let datePickerOptions = {
    wrap: true,
    onReady: (selectedDates, dateStr, instance) => {
        instance.setDate(currentDateFilter, false, "Y-m-d");
        // console.log(selectedDates);
        // console.log(dateStr);
        // console.log(instance);
    },
    onChange: (selectedDates, dateStr, instance) => {
        let dateFilterForm = document.getElementById("djetler-date-filter-form");
        dateFilterForm.submit();
    }
};

let djetlerDate = flatpickr('#djetler-date-picker', datePickerOptions);

