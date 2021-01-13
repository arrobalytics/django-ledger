import {DjangoLedgerApp} from "./DjangoLedgerApp";
import {NetPayablesChart, NetReceivablesChart, PnLChart} from "./AppCharts";
import Iconify from '@iconify/iconify';

let app = new DjangoLedgerApp();


export function renderPnLChart(selector: string, entitySlug: string, startDate: string, endDate: string) {
    return new PnLChart(selector, entitySlug, startDate, endDate);
}

export function renderNetPayablesChart(selector: string, entitySlug: string, startDate: string, endDate: string) {
    return new NetPayablesChart(selector, entitySlug, startDate, endDate);
}

export function renderNetReceivablesChart(selector: string, entitySlug: string, startDate: string, endDate: string) {
    return new NetReceivablesChart(selector, entitySlug, startDate, endDate);
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
    }
}

export function onChangeItem(htmlInput: HTMLInputElement) {
    console.log(+htmlInput.value)
}

export {Iconify};