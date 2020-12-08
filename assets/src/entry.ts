import {DjangoLedgerApp} from "./DjangoLedgerApp";
import {NetPayablesChart, IncomeExpensesChart, NetReceivablesChart} from "./AppCharts";
import Iconify from '@iconify/iconify';

let app = new DjangoLedgerApp();


export function renderInEChart(selector: string, entitySlug: string) {
    return new IncomeExpensesChart(selector, entitySlug);
}

export function renderNetPayablesChart(selector: string, entitySlug: string) {
    return new NetPayablesChart(selector, entitySlug);
}

export function renderNetReceivablesChart(selector: string, entitySlug: string) {
    return new NetReceivablesChart(selector, entitySlug);
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


export {Iconify};