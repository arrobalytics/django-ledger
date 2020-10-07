import Vue from 'vue';
import flatpickr from "flatpickr";


export class DjetlerApp {

    dateFilters: any | null = null;
    endDateFilters: any | null = null;
    vueInstance: Vue | null = null;

    constructor() {

        document.addEventListener('DOMContentLoaded', () => {
            (document.querySelectorAll('.notification .delete') || []).forEach(($delete) => {
                let $notification: any;
                $notification = $delete.parentNode;
                $delete.addEventListener('click', () => {
                    $notification.parentNode.removeChild($notification);
                });
            });
        });
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
                        // @ts-ignore
                        $target.classList.toggle('is-active');

                    });
                });
            }
        });
        document.addEventListener('DOMContentLoaded', () => {
            (document.querySelectorAll('.djetler-set-entity-form-input') || []).forEach(f => {
                f.addEventListener('change', this.setEntityFilter);
            });
        });

        this.endDateFilters = flatpickr(".djetler-end-date-icon-filter", this.getFlatPickrOptions(false));
        this.dateFilters = flatpickr(".djetler-date-filter", this.getFlatPickrOptions(true));

    }

    getFlatPickrOptions(inline: boolean = false) {
        if (!inline) {
            return {
                wrap: !inline,
                inline: inline,
                onChange: (selectedDates: any, dateStr: String, instance: any) => {
                    let formId = instance._input.classList[1].split("-")[5];
                    let dateFilterForm = document.getElementById("djetler-end-date-icon-filter-form-" + formId);
                    // @ts-ignore
                    dateFilterForm.submit();
                }
            };
        } else {
            return {
                wrap: !inline,
                inline: inline,
                onChange: (selectedDates: any, dateStr: String, instance: any) => {
                    let formId = instance._input.classList[1].split("-")[5];
                    let dateFilterForm = document.getElementById("djetler-end-date-icon-filter-form-" + formId);
                    // @ts-ignore
                    dateFilterForm.submit();
                }
            };
        }
    }

    setEntityFilter(event: Event) {

        let target: EventTarget | null = event.target;
        if (target) {
            // @ts-ignore
            let klass: string = target['classList'][2];
            let formId = klass.split("-")[4];
            let defaultEntityForm = document.getElementById("djetler-set-entity-form-" + formId);
            // @ts-ignore
            defaultEntityForm.submit();
            // console.log(defaultEntityForm);
        }
        // @ts-ignore
        // defaultEntityForm.submit();
    }

    public textLog() {
        console.log('hello!')
    }

}
