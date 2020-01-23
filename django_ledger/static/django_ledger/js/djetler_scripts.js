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

