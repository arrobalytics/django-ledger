import {DjetlerApp} from "./DjetlerApp";
import {RevenueAndNetIncome} from "./AppCharts";


export function startDJLApp() {
    return new DjetlerApp();
}

export function renderRnNIChart(selector: string, entitySlug: string) {
    return new RevenueAndNetIncome(selector, entitySlug);
}