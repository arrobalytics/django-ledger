// Dismiss Notifications
document.addEventListener('DOMContentLoaded', () => {
    (document.querySelectorAll('.notification .delete') || []).forEach(($delete) => {
        $notification = $delete.parentNode;
        $delete.addEventListener('click', () => {
            $notification.parentNode.removeChild($notification);
        });
    });
});

// Change entity from Nav
function setDefaultEntity() {
    let defaultEntityForm = document.getElementById("djetler-set-entity-form");
    defaultEntityForm.submit()
}

let djetlerDate = flatpickr('#djetler-date-picker', {});
console.log(djetlerDate);