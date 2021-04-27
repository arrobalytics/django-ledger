import {DjangoLedgerApp} from "./DjangoLedgerApp";
import {NetPayablesChart, NetReceivablesChart, PnLChart} from "./AppCharts";
import Iconify from '@iconify/iconify';

// @ts-ignore
import * as Pikaday from 'pikaday';
// import Vue from 'vue';
// import DatePicker from "./vue/DatePicker";

let app = new DjangoLedgerApp();


export function renderPnLChart(selector: string, entitySlug: string, fromDate: string, toDate: string) {
    return new PnLChart(selector, entitySlug, fromDate, toDate);
}

export function renderNetPayablesChart(selector: string, entitySlug: string, fromDate: string, toDate: string) {
    return new NetPayablesChart(selector, entitySlug, fromDate, toDate);
}

export function renderNetReceivablesChart(selector: string, entitySlug: string, fromDate: string, toDate: string) {
    return new NetReceivablesChart(selector, entitySlug, fromDate, toDate);
}

export function showModal(modalId: string) {
    let modalElement = document.getElementById(modalId);
    if (modalElement) {
        modalElement.classList.add('is-active', 'is-clipped')
    }
}

export function closeModal(modalId: string) {
    let modalElement = document.getElementById(modalId);
    if (modalElement) {
        modalElement.classList.remove('is-active', 'is-clipped')
    }
}

export function toggleModal(modalId: string) {
    let modalElement = document.getElementById(modalId);
    if (modalElement) {
        modalElement.classList.toggle('is-active')
        modalElement.classList.toggle('is-clipped')
    }
}

export function submitForm(formName: string, modalId: string) {
    let form = document.forms.namedItem(formName);
    if (form) {
        form.submit()
        if (modalId) {
            closeModal(modalId)
        }
    }
}


export function toggleDropdown(buttonId: string) {
    let button: HTMLElement | null = document.getElementById(buttonId)
    if (button) {
        !button.classList.contains('is-active') ? button.classList.add('is-active') : button.classList.remove('is-active')
    }
}

export function calculateItemTotal(
    totalItemId: string,
    quantityItemId: string,
    unitCostId: string) {

    let quantityItemElement: HTMLElement | null = document.getElementById(quantityItemId)
    let unitCostElement: HTMLElement | null = document.getElementById(unitCostId)
    let totalItemCostElement: HTMLElement | null = document.getElementById(totalItemId)

    if (totalItemCostElement && quantityItemElement && unitCostElement) {
        let unitCost = unitCostElement
        let quantity = quantityItemElement
        console.log(unitCost, quantity);
        // totalItemCostElement.innerHTML = String(unitCost * quantity);
        // totalItemCostElement.innerHTML = String(unitCost * quantity);
    }
}


export function getCalendar(htmlId: string, baseUrl: string) {
    let el = document.getElementById(htmlId)
    const bUrl = el!.dataset.baseurl
    return new Pikaday({
        field: el,

        onSelect(value: Date) {
            const y = value.getFullYear();
            const m = value.getMonth() + 1;
            const d = value.getDate();
            window.location.href = `${baseUrl}date/${y}/${m}/${d}/`
        }
    })
}

// export function getCalendarVue(htmlId: string, baseUrl: string) {
//     const htmlIdVue = '#' + htmlId;
//     return new Vue({
//         el: htmlIdVue,
//         components: {
//             DatePicker
//         }
//     })
// }

export {Iconify};