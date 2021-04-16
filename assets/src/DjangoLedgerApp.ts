import Vue from 'vue';


export class DjangoLedgerApp {

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

            const $navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);

            if ($navbarBurgers.length > 0) {

                $navbarBurgers.forEach(el => {
                    el.addEventListener('click', () => {
                        const target = el.dataset.target;
                        const $target = document.getElementById(target);
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
            if (defaultEntityForm) {
                // @ts-ignore
                defaultEntityForm.submit();
            }
        }
    }
}
